# ================================================================
#  app.py  –  Social‑Media Analysis backend (Flask + MySQL)
# ================================================================
from flask import Flask, request, jsonify
import mysql.connector, json, re
from contextlib import contextmanager
from datetime import datetime

app = Flask(__name__)

# ---------------------------------------------------------------
#  DB connection helper  (simple for coursework; prod → pool)
# ---------------------------------------------------------------
with open("db_config.json") as f:
    DB_CFG = json.load(f)

@contextmanager
def db_cursor():
    conn = mysql.connector.connect(**DB_CFG)
    cur = conn.cursor(dictionary=True,buffered=True)
    try:
        yield conn, cur
    except mysql.connector.Error as e:
        # Optional: rollback on errors if needed
        conn.rollback()
        raise e
    finally:
        try:
            # This clears unread results from SELECT queries (if any)
            try:
                while cur.next_result():
                    cur.fetchall()
            except:
                pass
            cur.close()
        except mysql.connector.errors.InternalError:
            pass
        conn.close()
# ---------------------------------------------------------------
#  Small utilities
# ---------------------------------------------------------------
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$")

def valid_datetime(s):
    if not DATE_RX.fullmatch(s.strip()):
        return False
    fmt = "%Y-%m-%d %H:%M:%S" if " " in s else "%Y-%m-%d"
    try:
        datetime.strptime(s, fmt)
        return True
    except ValueError:
        return False

def bad(msg, code=400):
    return jsonify({"error": msg}), code

def field_pct(cur, pid: int, post_ids=None):
    if post_ids:
        in_clause, in_vals = sql_in(post_ids)
        cur.execute(
            f"SELECT COUNT(*) AS tot FROM ProjectPost "
            f"WHERE project_id=%s AND post_id IN {in_clause}",
            (pid, *in_vals),
        )
    else:
        cur.execute(
            "SELECT COUNT(*) AS tot FROM ProjectPost WHERE project_id=%s", (pid,)
        )
    total = cur.fetchone()["tot"] or 1

    subset_sql, subset_vals = sql_in(post_ids) if post_ids else ("", ())
    subset_filter = f"AND pp.post_id IN {subset_sql}" if post_ids else ""

    cur.execute(
        f"""
        SELECT f.name, COUNT(ar.id) AS filled
        FROM   ProjectField f
        LEFT   JOIN AnalysisResult ar ON ar.field_id = f.id
        LEFT   JOIN ProjectPost pp ON pp.id = ar.project_post_id
                                   AND pp.project_id = %s {subset_filter}
        GROUP  BY f.id
        """,
        (pid, *subset_vals),
    )
    return {
        row["name"]: f"{round(row['filled'] / total * 100, 2):.2f}%"
        for row in cur.fetchall()
    }

def sql_in(ids):
    """Return ('%s,%s,...', tuple(ids)) for a parameterized IN clause."""
    if not ids:
        return "(NULL)", ()         # will never match
    placeholders = ",".join(["%s"] * len(ids))
    return f"({placeholders})", tuple(ids)

# ===============================================================
#  1.  DATA‑ENTRY ROUTES
# ===============================================================
@app.route("/add_project", methods=["POST"])
def add_project():
    """
    JSON payload
    ------------
    {
        "name"               : "Election‑2025 Sentiment",
        "manager_first_name" : "Dana",
        "manager_last_name"  : "Ng",
        "institute"          : "UTD Social Lab",
        "start_date"         : "2025-01-15",
        "end_date"           : "2025-06-30",
        "posts"              : [12, 18, 44]          #  ← optional
    }
    """
    d = request.json or {}

    # ----- 1. mandatory fields ------------------------------------------
    required = ("name", "institute", "start_date", "end_date")
    if any(k not in d or not d[k] for k in required):
        return bad("Missing project fields")

    try:
        start_dt = datetime.strptime(d["start_date"], "%Y-%m-%d")
        end_dt   = datetime.strptime(d["end_date"],   "%Y-%m-%d")
    except ValueError:
        return bad("Dates must be YYYY‑MM‑DD")              # 400
    if end_dt < start_dt:
        return bad("end_date must be on or after start_date")  # 400

    # optional list-of-post IDs
    post_ids = d.get("posts", [])
    if post_ids and not all(isinstance(p, int) for p in post_ids):
        return bad("`posts` must be a list of integers")

    with db_cursor() as (conn, cur):
    # ----- 2. institute  (get or create) ----------------------------
        cur.execute("SELECT id FROM Institute WHERE name=%s", (d["institute"],))
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO Institute (name) VALUES (%s)", (d["institute"],))
            institute_id = cur.lastrowid
        else:
            institute_id = row[0]

        # ----- 3. create project  (catch duplicate‑name / bad‑date) -----
        try:
            cur.execute(
                """
                INSERT INTO Project
                    (name, manager_first_name, manager_last_name,
                    institute_id, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    d["name"],
                    d.get("manager_first_name"),
                    d.get("manager_last_name"),
                    institute_id,
                    d["start_date"],
                    d["end_date"],
                ),
            )
        except mysql.connector.IntegrityError as e:
            # ER_DUP_ENTRY  = 1062   (UNIQUE name)
            # ER_CHECK_CONSTRAINT_VIOLATED = 3819 (date CHECK fail, MySQL 8)
            if e.errno == 1062:
                return jsonify({"status": "Project with this name already exists"}), 409
            if e.errno == 3819:
                return jsonify({"status": "end_date must be on or after start_date"}), 400
            # any other integrity error
            return jsonify({"status": "Invalid project data"}), 400

        project_id = cur.lastrowid

        # ----- 4. optionally link supplied posts -----------------------
        if post_ids:
            placeholders = ",".join(["%s"] * len(post_ids))
            cur.execute(
                f"SELECT id FROM Post WHERE id IN ({placeholders})", tuple(post_ids)
            )
            valid_ids = [r["id"] for r in cur.fetchall()]
            for pid in valid_ids:
                cur.execute(
                    "INSERT IGNORE INTO ProjectPost (project_id, post_id) VALUES (%s,%s)",
                    (project_id, pid),
                )

        conn.commit()

    return jsonify({"status": "Project added", "project_id": project_id}), 201


@app.route("/list_projects", methods=["GET"])
def list_projects():
    """Return all projects as a list of {id, name}"""
    with db_cursor() as (conn, cur):
        cur.execute("SELECT id, name FROM Project ORDER BY name")
        projects = cur.fetchall()
    return jsonify({"projects": projects})

@app.route("/get_posts_in_range")
def get_posts_in_range():
    start = request.args.get("start")
    end = request.args.get("end")

    if not valid_datetime(start) or not valid_datetime(end):
        return jsonify({"posts": []}), 400

    with db_cursor() as (conn, cur):
        cur.execute("""
            SELECT 
                Post.id, Post.post_time, `User`.username, SocialMedia.name AS social_media
            FROM Post
            JOIN `User` ON Post.user_id = `User`.id
            JOIN SocialMedia ON Post.social_media_id = SocialMedia.id
            WHERE DATE(Post.post_time) BETWEEN %s AND %s
            ORDER BY Post.post_time
        """, (start, end))

        posts = [
            {
                "id": row["id"],
                "post_time": row["post_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "username": row["username"],
                "social_media": row["social_media"]
            }
            for row in cur.fetchall()
        ]

    return jsonify({"posts": posts})

@app.route("/list_usernames")
def list_usernames():
    with db_cursor() as (conn, cur):
        cur.execute("SELECT DISTINCT username FROM `User`")
        return jsonify({"usernames": [r['username'] for r in cur.fetchall()]})

@app.route("/list_user_platforms")
def list_user_platforms():
    username = request.args.get("username")
    with db_cursor() as (conn, cur):
        cur.execute("""
            SELECT DISTINCT s.name
            FROM Post p
            JOIN `User` u ON p.user_id = u.id
            JOIN SocialMedia s ON p.social_media_id = s.id
            WHERE u.username = %s
        """, (username,))
        return jsonify({"platforms": [r['name'] for r in cur.fetchall()]})

@app.route("/list_user_posts")
def list_user_posts():
    username = request.args.get("username")
    platform = request.args.get("platform")

    with db_cursor() as (conn, cur):
        cur.execute("""
            (
                SELECT 
                    p.id AS id,
                    p.post_time AS post_time,
                    p.content AS content,
                    'original' AS post_type,
                    NULL AS original_post_id,
                    u.username AS username
                FROM Post p
                JOIN `User` u ON p.user_id = u.id
                JOIN SocialMedia s ON p.social_media_id = s.id
                WHERE u.username = %s AND s.name = %s
                  AND NOT EXISTS (
                      SELECT 1 FROM Repost r WHERE r.repost_post_id = p.id
                  )
            )
            UNION ALL
            (
                SELECT 
                    p.id AS id,
                    p.post_time AS post_time,
                    p.content AS content,
                    'repost' AS post_type,
                    r.original_post_id AS original_post_id,
                    u.username AS username
                FROM Post p
                JOIN Repost r ON p.id = r.repost_post_id
                JOIN `User` u ON p.user_id = u.id
                JOIN SocialMedia s ON p.social_media_id = s.id
                WHERE u.username = %s AND s.name = %s
            )
            ORDER BY post_time
        """, (username, platform, username, platform))

        posts = [
            {
                "id": r["id"],
                "post_time": r["post_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "content": r["content"],
                "type": r["post_type"],
                "original_post_id": r["original_post_id"],
                "username": r["username"]
            }
            for r in cur.fetchall()
        ]

    return jsonify({"posts": posts})



@app.route("/add_post", methods=["POST"])
def add_post():
    d = request.json or {}
    required = ("username", "social_media", "post_time", "content")
    if any(k not in d or not d[k] for k in required):
        return bad("Missing post fields")
    if not valid_datetime(d["post_time"]):
        return bad("post_time must be YYYY‑MM‑DD HH:MM:SS")

    with db_cursor() as (conn, cur):
        # social‑media (get or create)
        cur.execute("SELECT id FROM SocialMedia WHERE name=%s", (d["social_media"],))
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO SocialMedia (name) VALUES (%s)", (d["social_media"],))
            media_id = cur.lastrowid
        else:
            media_id = row["id"]

        # user (get or create)
        cur.execute(
            "SELECT id FROM `User` WHERE username=%s AND social_media_id=%s",
            (d["username"], media_id),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                INSERT INTO `User`
                  (username, social_media_id, first_name, last_name,
                   country_of_birth, country_of_residence, age, gender, verified)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    d["username"],
                    media_id,
                    d.get("first_name"),
                    d.get("last_name"),
                    d.get("birth_country"),
                    d.get("residence_country"),
                    d.get("age"),
                    d.get("gender"),
                    d.get("verified", False),
                ),
            )
            user_id = cur.lastrowid
        else:
            user_id = row["id"]

        # duplicate check
        cur.execute(
            """
            SELECT 1 FROM Post
            WHERE user_id=%s AND social_media_id=%s AND post_time=%s
            """,
            (user_id, media_id, d["post_time"]),
        )
        if cur.fetchone():
            return jsonify({"status": "Post already exists"}), 200

        # insert post
        cur.execute(
            """
            INSERT INTO Post
              (user_id, social_media_id, post_time, content, city, state, country,
               likes, dislikes, multimedia, media_url)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                user_id,
                media_id,
                d["post_time"],
                d["content"],
                d.get("city"),
                d.get("state"),
                d.get("country"),
                int(d.get("likes", 0)),
                int(d.get("dislikes", 0)),
                bool(d.get("multimedia", False)),
                d.get("media_url"),
            ),
        )
        conn.commit()
    return jsonify({"status": "Post added"}), 201

@app.route("/repost", methods=["POST"])
def repost():
    data = request.json
    original_post_id = data.get("original_post_id")
    reposter_username = data.get("reposter_username")
    repost_time = data.get("repost_time")

    if not original_post_id or not reposter_username or not repost_time:
        return jsonify({"status": "Missing required fields"}), 400

    if not valid_datetime(repost_time):
        return jsonify({"status": "Invalid repost time format"}), 400

    with db_cursor() as (conn, cur):
        try:
            # Step 1: Get original post content and platform
            cur.execute("SELECT content, social_media_id, post_time FROM Post WHERE id = %s", (original_post_id,))
            original_post = cur.fetchone()
            if not original_post:
                return jsonify({"status": "Original post not found"}), 404

            # Step 2: Validate repost time
            original_time = original_post["post_time"]
            repost_dt = datetime.strptime(repost_time, "%Y-%m-%d %H:%M:%S")
            if repost_dt <= original_time:
                return jsonify({"status": "Repost time must be after original post time"}), 400

            # Step 3: Get reposter ID
            cur.execute("SELECT id FROM `User` WHERE username = %s", (reposter_username,))
            user_result = cur.fetchone()
            if not user_result:
                cur.fetchall()
                return jsonify({"status": "Reposter user not found"}), 404
            reposter_id = user_result["id"]

            # Step 4: Create new post as a repost
            cur.execute("""
                INSERT INTO Post (user_id, social_media_id, post_time, content)
                VALUES (%s, %s, %s, %s)
            """, (
                reposter_id,
                original_post["social_media_id"],
                repost_time,
                original_post["content"]
            ))
            repost_post_id = cur.lastrowid

            # Step 5: Insert into Repost linking original and new
            cur.execute("""
                INSERT INTO Repost (original_post_id, repost_post_id, reposter_id, repost_time)
                VALUES (%s, %s, %s, %s)
            """, (original_post_id, repost_post_id, reposter_id, repost_time))
            conn.commit()

        except mysql.connector.IntegrityError:
            conn.rollback()
            return jsonify({"status": "Duplicate repost not allowed"}), 400

    return jsonify({"status": "Repost recorded"}), 201


@app.route("/assign_post_to_project", methods=["POST"])
def assign_post_to_project():
    d = request.json or {}
    if "project_id" not in d or "post_id" not in d:
        return bad("project_id and post_id required")
    with db_cursor() as (conn, cur):
        cur.execute(
            "INSERT IGNORE INTO ProjectPost (project_id, post_id) VALUES (%s,%s)",
            (d["project_id"], d["post_id"]),
        )
    return jsonify({"status": "Post assigned"}), 201


@app.route("/add_field", methods=["POST"])
def add_field():
    d = request.json or {}
    if "project_id" not in d or "field_name" not in d:
        return bad("project_id and field_name required")
    with db_cursor() as (conn, cur):
        cur.execute(
            "INSERT IGNORE INTO ProjectField (name, project_id) VALUES (%s,%s)",
            (d["field_name"], d["project_id"]),
        )
    return jsonify({"status": "Field added"}), 201


@app.route("/enter_analysis_result", methods=["POST"])
def enter_analysis_result():
    """
    JSON payload:
    {
      "project_id": 3,
      "post_id":    1,
      "results": {
          "sentiment": "positive",
          "objects":   "4"
      }
    }
    This handler will:
     • create ProjectPost(project_id, post_id) if missing,
     • create ProjectField(name, project_id) for any new field_name,
     • upsert the AnalysisResult for each field/value.
    """
    d = request.json or {}
    if any(k not in d for k in ("project_id", "post_id", "results")):
        return bad("project_id, post_id, and results are required", 400)

    with db_cursor() as (conn, cur):
        # 1) ensure the post is linked to the project
        cur.execute(
            "SELECT id FROM ProjectPost WHERE project_id=%s AND post_id=%s",
            (d["project_id"], d["post_id"])
        )
        row = cur.fetchone()
        if not row:
            # link it automatically
            cur.execute(
                "INSERT INTO ProjectPost (project_id, post_id) VALUES (%s, %s)",
                (d["project_id"], d["post_id"])
            )
            project_post_id = cur.lastrowid
        else:
            project_post_id = row['id']

        # 2) upsert each field/value pair, auto‑creating fields as needed
        for field_name, value in d["results"].items():
            # 2a) get or create the field
            cur.execute(
                "SELECT id FROM ProjectField WHERE name=%s AND project_id=%s",
                (field_name, d["project_id"])
            )
            f = cur.fetchone()
            if f:
                field_id = f['id']
            else:
                cur.execute(
                    "INSERT INTO ProjectField (name, project_id) VALUES (%s, %s)",
                    (field_name, d["project_id"])
                )
                field_id = cur.lastrowid

            # 2b) upsert the analysis result
            cur.execute(
                """
                INSERT INTO AnalysisResult 
                  (project_post_id, field_id, value)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  value = VALUES(value)
                """,
                (project_post_id, field_id, str(value))
            )
        conn.commit()

    return jsonify({"status": "Results saved"}), 201

@app.route("/query_project_analysis", methods=["GET"])
def query_project_analysis():
    pid = request.args.get("project_id")
    name = request.args.get("project_name")
    if not pid and not name:
        return bad("Provide project_id or project_name")

    with db_cursor() as (conn, cur):
        if name and not pid:
            cur.execute("SELECT id FROM Project WHERE name=%s", (name,))
            row = cur.fetchone()
            if not row:
                return bad("Project not found", 404)
            pid = row["id"]

        # ---- 1. all posts in the experiment --------------------------------
        cur.execute(
            """
            SELECT p.id, p.content, sm.name AS social_media,
                   u.username, p.post_time
            FROM Post p
            JOIN ProjectPost pp ON pp.post_id = p.id
            JOIN `User`       u ON p.user_id  = u.id
            JOIN SocialMedia sm ON p.social_media_id = sm.id
            WHERE pp.project_id = %s
            """,
            (pid,),
        )
        posts = cur.fetchall()

        # ---- 2. attach per‑post results ------------------------------------
        for post in posts:
            cur.execute(
                """
                SELECT f.name, ar.value
                FROM AnalysisResult ar
                JOIN ProjectField f ON ar.field_id = f.id
                JOIN ProjectPost pp ON ar.project_post_id = pp.id
                WHERE pp.project_id = %s AND pp.post_id = %s
                """,
                (pid, post["id"]),
            )
            post["results"] = {r["name"]: r["value"] for r in cur.fetchall()}

        # ---- 3. field % based on ALL posts in experiment -------------------
        completion = field_pct(cur, pid)

    return jsonify({"posts": posts, "field_completion": completion})


@app.route("/search_post", methods=["GET"])
def search_post():
    # Parse incoming parameters
    social_media = request.args.get("social_media", "").strip()
    username     = request.args.get("username", "").strip()
    first_name   = request.args.get("first_name", "").strip()
    last_name    = request.args.get("last_name", "").strip()
    from_time    = request.args.get("from_time", "").strip()
    to_time      = request.args.get("to_time", "").strip()

    # Build base query
    query = """
        SELECT 
            Post.id,
            Post.content AS text,
            Post.post_time,
            SocialMedia.name AS social_media,
            `User`.username,
            Project.name AS project_name
        FROM Post
        JOIN `User`            ON Post.user_id = `User`.id
        JOIN SocialMedia       ON Post.social_media_id = SocialMedia.id
        LEFT JOIN ProjectPost  ON Post.id = ProjectPost.post_id
        LEFT JOIN Project      ON ProjectPost.project_id = Project.id
        WHERE 1=1
    """

    params = []

    # Dynamically apply filters
    if social_media:
        query += " AND SocialMedia.name = %s"
        params.append(social_media)
    if username:
        query += " AND `User`.username = %s"
        params.append(username)
    if first_name:
        query += " AND LOWER(TRIM(`User`.first_name)) = %s"
        params.append(first_name.lower().strip())
    if last_name:
        query += " AND LOWER(TRIM(`User`.last_name)) = %s"
        params.append(last_name.lower().strip())
    if from_time and to_time:
        query += " AND Post.post_time BETWEEN %s AND %s"
        try:
            from_dt = datetime.strptime(from_time, "%Y-%m-%d %H:%M:%S")
            to_dt   = datetime.strptime(to_time,   "%Y-%m-%d %H:%M:%S")
            params.append(from_dt)
            params.append(to_dt)
        except ValueError:
            return jsonify({"error": "Invalid datetime format"}), 400

    query += " ORDER BY Post.post_time DESC"

    # Execute query
    with db_cursor() as (_, cur):
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

    # Organize posts by project/experiment
    result = {}
    for row in rows:
        proj = row["project_name"] or "Unassigned"
        if proj not in result:
            result[proj] = {"posts": []}
        result[proj]["posts"].append({
            "id": row["id"],
            "text": row["text"] or "",
            "post_time": row["post_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "social_media": row["social_media"],
            "username": row["username"]
        })

    return jsonify({"experiments": result})

@app.route("/combo_post_to_experiment", methods=["GET"])
def combo_post_to_experiment():
    # Parse filters from request
    social_media = request.args.get("social_media", "").strip()
    username     = request.args.get("username", "").strip()
    first_name   = request.args.get("first_name", "").strip()
    last_name    = request.args.get("last_name", "").strip()
    from_time    = request.args.get("from_time", "").strip()
    to_time      = request.args.get("to_time", "").strip()

    # Step 1: Use same filtering logic as search_post()
    query = """
        SELECT 
            Post.id,
            Post.content AS text,
            Post.post_time,
            SocialMedia.name AS social_media,
            `User`.username,
            Project.name AS project_name
        FROM Post
        JOIN `User`            ON Post.user_id = `User`.id
        JOIN SocialMedia       ON Post.social_media_id = SocialMedia.id
        LEFT JOIN ProjectPost  ON Post.id = ProjectPost.post_id
        LEFT JOIN Project      ON ProjectPost.project_id = Project.id
        WHERE 1=1
    """
    params = []

    if social_media:
        query += " AND SocialMedia.name = %s"
        params.append(social_media)
    if username:
        query += " AND `User`.username = %s"
        params.append(username)
    if first_name:
        query += " AND LOWER(TRIM(`User`.first_name)) = %s"
        params.append(first_name.lower().strip())
    if last_name:
        query += " AND LOWER(TRIM(`User`.last_name)) = %s"
        params.append(last_name.lower().strip())
    if from_time and to_time:
        try:
            from_dt = datetime.strptime(from_time, "%Y-%m-%d %H:%M:%S")
            to_dt   = datetime.strptime(to_time,   "%Y-%m-%d %H:%M:%S")
            query += " AND Post.post_time BETWEEN %s AND %s"
            params.append(from_dt)
            params.append(to_dt)
        except ValueError:
            return jsonify({"error": "Invalid datetime format"}), 400

    query += " ORDER BY Post.post_time DESC"

    with db_cursor(dictionary=True) as (_, cur):
        cur.execute(query, tuple(params))
        posts = cur.fetchall()

        if not posts:
            return jsonify({"experiments": {}})

        # Step 2: Extract post IDs and lookup
        post_ids = [p["id"] for p in posts]
        post_lookup = {p["id"]: p for p in posts}

        # Step 3: Fetch project association + results for those post_ids
        format_strings = ','.join(['%s'] * len(post_ids))
        cur.execute(f"""
            SELECT
                Project.name AS project_name,
                Post.id AS post_id,
                ProjectPost.id AS project_post_id,
                ProjectField.name AS field_name,
                AnalysisResult.value
            FROM ProjectPost
            JOIN Post           ON ProjectPost.post_id = Post.id
            JOIN Project        ON ProjectPost.project_id = Project.id
            LEFT JOIN AnalysisResult ON ProjectPost.id = AnalysisResult.project_post_id
            LEFT JOIN ProjectField   ON AnalysisResult.field_id = ProjectField.id
            WHERE Post.id IN ({format_strings})
        """, post_ids)
        rows = cur.fetchall()

    # Step 4: Organize by experiment
    experiments = {}
    field_totals = {}

    for row in rows:
        exp = row["project_name"]
        pid = row["post_id"]
        fld = row["field_name"]
        val = row["value"]

        if exp not in experiments:
            experiments[exp] = {"posts": [], "field_completion": {}}
            field_totals[exp] = {}

        # Attach result to the correct post
        if "results" not in post_lookup[pid]:
            post_lookup[pid]["results"] = {}
        if fld:
            post_lookup[pid]["results"][fld] = val
            field_totals[exp][fld] = field_totals[exp].get(fld, 0) + 1

        # Only add post to experiment once
        if not any(p["id"] == pid for p in experiments[exp]["posts"]):
            experiments[exp]["posts"].append(post_lookup[pid])

    # Step 5: Calculate % completion
    for exp, meta in experiments.items():
        total_posts = len(meta["posts"])
        for fld, count in field_totals[exp].items():
            meta["field_completion"][fld] = f"{(count / total_posts * 100):.1f}%"

    return jsonify({"experiments": experiments})

# ===============================================================
#  MAIN
# ===============================================================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)

