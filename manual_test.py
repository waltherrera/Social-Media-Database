import os
import mysql.connector
from mysql.connector import errorcode

# Configuration for database connection
db_cfg = {
    "host": "localhost",
    "user": "root",
    "password": "75399357",
    "database": "SocialMediaDatabaseProject"
}

# Locate init_db.sql relative to this script's directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SQL_FILE = os.path.join(BASE_DIR, "schema", "init_db.sql")

# Read SQL script
print(f"Recreating schema from {SQL_FILE}...")
with open(SQL_FILE, 'r') as f:
    sql_script = f.read()

# Connect and recreate schema
def recreate_schema():
    conn = mysql.connector.connect(**db_cfg)
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
    for statement in sql_script.split(';'):
        stmt = statement.strip()
        if stmt:
            cur.execute(stmt + ';')
    cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()
    cur.close()
    conn.close()

recreate_schema()
print("Schema recreation complete.\n")

# Helper to run a test and print result

def run_test(name, func, expect_success=True):
    try:
        func()
        if expect_success:
            print(f"[PASS] {name}")
        else:
            print(f"[FAIL] {name} → expected failure but succeeded")
    except mysql.connector.Error as e:
        if expect_success:
            print(f"[FAIL] {name} → unexpected error -> {e.errno} ({e.sqlstate}): {e.msg}")
        else:
            print(f"[PASS] {name} → failed as expected -> {e.errno} ({e.sqlstate}): {e.msg}")

# Begin tests
conn = mysql.connector.connect(**db_cfg)
cur = conn.cursor()

# 1. Insert SocialPlatform 'Twitter'
# Sanity‑check that a brand‑new social‑platform row inserts cleanly
#   (AUTO_INCREMENT PK + UNIQUE(name) on SocialPlatform).
def test_socialplatform():
    cur.execute("INSERT INTO SocialPlatform (name) VALUES (%s)", ("Twitter",))

run_test("Insert SocialPlatform 'Twitter'", test_socialplatform)

# 2. Insert User alice@Twitter
# Verify a user can be created for that platform and that the
#   FK User.platform_id works; also sets up the (username, platform_id)
#   composite‑UNIQUE for later negative tests.
def test_user():
    cur.execute(
        "INSERT INTO `User` (username, platform_id) VALUES (%s, %s)",
        ("alice", cur.lastrowid)
    )

run_test("Insert User alice@Twitter", test_user)
user_id = cur.lastrowid
platform_id = cur.lastrowid  # same as above insert ID

# 3. Insert first Post by alice
# Insert a perfectly valid post to prove the Post table accepts
#   FK references to User & SocialPlatform plus default/check columns.
def test_first_post():
    cur.execute(
        "INSERT INTO Post (user_id, platform_id, post_time, content) VALUES (%s, %s, %s, %s)",
        (user_id, platform_id, "2025-05-06 21:50:26", "Hello world post")
    )

run_test("Insert first Post by alice", test_first_post)
post_id = cur.lastrowid

# 4. Insert duplicate Post (same user/time) → expect failure
# Attempt a duplicate (user_id, platform_id, post_time) to confirm
#   the composite UNIQUE constraint `uq_post_time` blocks duplicates.
def test_duplicate_post():
    cur.execute(
        "INSERT INTO Post (user_id, platform_id, post_time, content) VALUES (%s, %s, %s, %s)",
        (user_id, platform_id, "2025-05-06 21:50:26", "Duplicate post")
    )

run_test("Insert duplicate Post (same user/time)", test_duplicate_post, expect_success=False)

# 5. Insert Post with negative likes → expect failure
# Try to violate `CHECK (likes >= 0)` to be sure the non‑negative
#   likes/dislikes rule is enforced at the DB level.
def test_negative_likes():
    cur.execute(
        "INSERT INTO Post (user_id, platform_id, post_time, content, likes) VALUES (%s, %s, %s, %s, %s)",
        (user_id, platform_id, "2025-05-06 22:00:00", "Bad likes post", -5)
    )

run_test("Insert Post with negative likes", test_negative_likes, expect_success=False)

# 6. Insert Institute 'MIT'
# Insert an institute row; simple smoke test for the reference table
#   and its UNIQUE(name) constraint.
def test_institute():
    cur.execute("INSERT INTO Institute (name) VALUES (%s)", ("MIT",))

run_test("Insert Institute 'MIT'", test_institute)
institute_id = cur.lastrowid

# 7. Insert Project 'ResearchX' linked to MIT
# Create a project tied to that institute to exercise the
#   FK Project.institute_id and the date‑range CHECK
#   (end_date must be ≥ start_date).
def test_project():
    cur.execute(
        "INSERT INTO Project (name, institute_id, start_date, end_date) VALUES (%s, %s, %s, %s)",
        ("ResearchX", institute_id, "2025-01-01", "2025-12-31")
    )

run_test("Insert Project 'ResearchX' linked to MIT", test_project)
project_id = cur.lastrowid

# 8. Link ProjectPost (ResearchX, Hello world post)
#   Link the project to the post in the junction table; proves both
#   FKs (to Project & Post) and the UNIQUE(project_id, post_id) pair.
def test_projectpost():
    cur.execute(
        "INSERT INTO ProjectPost (project_id, post_id) VALUES (%s, %s)",
        (project_id, post_id)
    )

run_test("Link ProjectPost (ResearchX, Hello world post)", test_projectpost)
link_id = cur.lastrowid

# 9. Create ProjectField 'sentiment' for ResearchX
#   Add a dynamic field (“sentiment”) to the project; verifies the
#   FK to Project and per‑project UNIQUE(field name).
def test_projectfield():
    cur.execute(
        "INSERT INTO ProjectField (project_id, name) VALUES (%s, %s)",
        (project_id, "sentiment")
    )

run_test("Create ProjectField 'sentiment' for ResearchX", test_projectfield)
field_id = cur.lastrowid

# 10. Upsert AnalysisResult for that link
# Upsert an AnalysisResult for that (project_post, field) pair;
#   confirms the UNIQUE(project_post_id, field_id) constraint and
#   shows ON DUPLICATE KEY UPDATE behaves as expected.
def test_analysisresult():
    cur.execute(
        "INSERT INTO AnalysisResult (project_post_id, field_id, value)"
        " VALUES (%s, %s, %s)"
        " ON DUPLICATE KEY UPDATE value=VALUES(value)",
        (link_id, field_id, "Positive")
    )

run_test("Upsert AnalysisResult for that link", test_analysisresult)

# 11. Insert Repost for non-existent post → expect failure
# Attempt to insert a Repost pointing at a non‑existent post to
#   ensure the FK Repost.original_post_id correctly prevents orphans.
def test_repost_fk():
    cur.execute(
        "INSERT INTO Repost (original_post_id, reposter_id, repost_time) VALUES (%s, %s, %s)",
        (999999, user_id, "2025-05-06 23:00:00")
    )

run_test("Insert Repost for non-existent post", test_repost_fk, expect_success=False)

# Cleanup
conn.rollback()
cur.close()
conn.close()