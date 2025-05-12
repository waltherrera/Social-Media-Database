"""
gui.py – Tkinter GUI for Social‑Media Analysis DB
-------------------------------------------------
Python 3.8+   |   pip install requests
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import requests, json
import datetime as _dt

API_URL = "http://localhost:5001"
#roots
root = tk.Tk()
root.title("Social‑Media Analysis DB")
root.geometry("950x720")
ttk.Style().theme_use("clam")

# right after ttk.Style().theme_use("clam")
style = ttk.Style()

# make all frames a light‑pink background
style.configure("TFrame", background="lightpink")
style.configure("TLabelFrame", background="lightpink")

# make all labels inherit the same bg
style.configure("TLabel", background="lightpink")

# make text entries sit on light pink too
style.configure("TEntry", fieldbackground="white", background="lightpink")

# style the notebook tabs and page area
style.configure("TNotebook", background="lightpink")
style.configure("TNotebook.Tab", background="lightpink")
style.map("TNotebook.Tab",
          background=[("selected", "#ffccd9")])

# your buttons darker pink, white text, and a hover‑brighten
style.configure("TButton",
                background="#cc3366",
                foreground="white")
style.map("TButton",
          background=[("active", "#ff6699")])

# comboboxes light pink
style.configure("TCombobox",
                fieldbackground="#ffe6f0",
                background="#ffe6f0")



nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True, padx=6, pady=6)


def iso(s: str) -> str:
    s = s.strip()
    if not s:
        raise ValueError("Empty date")
    fmt = "%Y-%m-%d %H:%M:%S" if " " in s else "%Y-%m-%d"
    return datetime.strptime(s, fmt).strftime(fmt)

def _iso_or_err(date_str: str) -> str:
    """Return YYYY‑MM‑DD if the string is valid; otherwise raise ValueError."""
    return _dt.datetime.strptime(date_str.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")


def post(endpoint: str, payload: dict, ok="Success"):
    try:
        r = requests.post(f"{API_URL}{endpoint}", json=payload, timeout=8)
        r.raise_for_status()
       # messagebox.showinfo("✓", r.json().get("status", ok))\
        toast(r.json().get("status", ok))
    except Exception as e:
        messagebox.showerror("Error", str(e))


def get(endpoint: str, params=None):
    try:
        r = requests.get(f"{API_URL}{endpoint}", params=params, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return None

def toast(msg, duration=3000):
    toast_lbl = tk.Label(root, text=msg, bg="#444", fg="white", font=("Segoe UI", 10, "bold"))
    toast_lbl.place(relx=0.5, rely=1.0, anchor="s")
    root.after(duration, toast_lbl.destroy)

#
# ======================================================================
# TAB 1 – Add Project  (now with optional post list)
# ======================================================================
t_proj = ttk.Frame(nb)
nb.add(t_proj, text="Add Project")

proj_vars = {
    "Project name*": tk.StringVar(),
    "Manager first name": tk.StringVar(),
    "Manager last name": tk.StringVar(),
    "Institute*": tk.StringVar(),
    "Start date (YYYY-MM-DD)*": tk.StringVar(),
    "End date (YYYY-MM-DD)*": tk.StringVar(),
    "Posts (IDs comma-sep)": tk.StringVar(),
}

post_checkboxes = []  # stores dynamically created checkbuttons
checkbox_frame = None

def parse_iso_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()

def fetch_posts_in_date_range():
    global checkbox_frame, post_checkboxes
    for cb in post_checkboxes:
        cb.destroy()
    post_checkboxes.clear()

    try:
        start = parse_iso_date(proj_vars["Start date (YYYY-MM-DD)*"].get())
        end = parse_iso_date(proj_vars["End date (YYYY-MM-DD)*"].get())
    except ValueError:
        return

    response = requests.get("http://localhost:5000/get_posts_in_range", params={"start": start, "end": end})
    if response.status_code != 200:
        return

    posts = response.json().get("posts", [])  # each post has: id, post_time, username, social_media

    if checkbox_frame:
        checkbox_frame.destroy()
    checkbox_frame = ttk.LabelFrame(t_proj, text="Select Posts in Date Range")
    checkbox_frame.grid(row=len(proj_vars), column=0, columnspan=2, padx=10, pady=5, sticky="ew")

    canvas = tk.Canvas(checkbox_frame, height=180)
    scrollbar = ttk.Scrollbar(checkbox_frame, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    checkbox_frame.columnconfigure(0, weight=1)

    checkbox_vars = []

    def update_post_ids_field():
        selected_ids = [str(pid) for var, pid in checkbox_vars if var.get() == 1]
        proj_vars["Posts (IDs comma-sep)"].set(",".join(selected_ids))

    # Header row
    header = ttk.Frame(scroll_frame)
    header.pack(fill="x", padx=4)
    ttk.Label(header, text="✓", width=3).grid(row=0, column=0)
    ttk.Label(header, text="Post ID", width=8).grid(row=0, column=1)
    ttk.Label(header, text="User", width=15).grid(row=0, column=2)
    ttk.Label(header, text="Time", width=20).grid(row=0, column=3)
    ttk.Label(header, text="Platform", width=12).grid(row=0, column=4)

    # Data rows
    for post in posts:
        pid = post.get("id")
        post_time = post.get("post_time", "N/A")
        username = post.get("username", "N/A")
        platform = post.get("social_media", "N/A")

        row = ttk.Frame(scroll_frame)
        row.pack(fill="x", anchor="w", padx=4)

        var = tk.IntVar(value=0)
        cb = ttk.Checkbutton(row, variable=var, command=update_post_ids_field)
        cb.grid(row=0, column=0, padx=2)
        ttk.Label(row, text=str(pid), width=8).grid(row=0, column=1, sticky="w")
        ttk.Label(row, text=username, width=15).grid(row=0, column=2, sticky="w")
        ttk.Label(row, text=post_time, width=20).grid(row=0, column=3, sticky="w")
        ttk.Label(row, text=platform, width=12).grid(row=0, column=4, sticky="w")

        post_checkboxes.append(row)
        checkbox_vars.append((var, pid))

def add_project():
    """
    Validate form fields and POST /add_project.
    Shows a toast on success, or an error dialog on failure.
    """
    # 1. gather + client‑side validation
    try:
        start_iso = _iso_or_err(proj_vars["Start date (YYYY-MM-DD)*"].get())
        end_iso   = _iso_or_err(proj_vars["End date (YYYY-MM-DD)*"].get())
        if end_iso < start_iso:
            return messagebox.showerror("Date error", "End‑date must be on or after start‑date")
    except ValueError:
        return messagebox.showerror("Bad date", "Dates must be YYYY‑MM‑DD")

    payload = {
        "name": proj_vars["Project name*"].get().strip(),
        "manager_first_name": proj_vars["Manager first name"].get().strip() or None,
        "manager_last_name":  proj_vars["Manager last name"].get().strip()  or None,
        "institute": proj_vars["Institute*"].get().strip(),
        "start_date": start_iso,
        "end_date":   end_iso,
    }

    if not payload["name"] or not payload["institute"]:
        return messagebox.showerror("Missing", "Name & Institute required")

    # only add posts if the user actually selected any
    ids_raw = proj_vars["Posts (IDs comma-sep)"].get().strip()
    if ids_raw:
        try:
            payload["posts"] = [int(i) for i in ids_raw.split(",") if i.strip()]
        except ValueError:
            return messagebox.showerror("Bad input", "Post IDs must be integers")

    # 2. send request
    try:
        r = requests.post(f"{API_URL}/add_project", json=payload, timeout=8)
    except Exception as e:
        return messagebox.showerror("Server error", str(e))

    # 3. handle response
    if r.status_code == 201:
        toast(r.json().get("status", "Project added"))
        load_projects()
    else:
        # show the server‑side message (e.g. date‑range rejection)
        msg = (r.json().get("status") or
               r.json().get("error")  or
               f"Error {r.status_code}")
        messagebox.showerror("Error", msg)



# ────────────────────────────────────────────────────────────────────────────
#  Draw the form
# ────────────────────────────────────────────────────────────────────────────
for r, (lbl, var) in enumerate(proj_vars.items()):
    ttk.Label(t_proj, text=lbl).grid(row=r, column=0, sticky="w", padx=3, pady=3)

    ent = ttk.Entry(t_proj, textvariable=var, width=45)
    ent.grid(row=r, column=1, sticky="ew", pady=3)

    if "Start date" in lbl or "End date" in lbl:
        ent.bind("<FocusOut>", lambda e: fetch_posts_in_date_range())

t_proj.columnconfigure(1, weight=1)

ttk.Button(
    t_proj, text="Create Project", command=add_project
).grid(row=len(proj_vars) + 2, column=0, columnspan=2, pady=10)
# ======================================================================
# TAB 2 – Add Post
# ======================================================================
t_post = ttk.Frame(nb)
nb.add(t_post, text="Add Post")

post_vars = {
    "Username*": tk.StringVar(),
    "Social media*": tk.StringVar(),
    "Post time (YYYY‑MM‑DD HH:MM:SS)*": tk.StringVar(),
    "City": tk.StringVar(),
    "State": tk.StringVar(),
    "Country": tk.StringVar(),
    "Likes": tk.StringVar(value="0"),
    "Dislikes": tk.StringVar(value="0"),
    "Media URL": tk.StringVar(),
    "First name": tk.StringVar(),
    "Last name": tk.StringVar(),
    "Birth country": tk.StringVar(),
    "Residence country": tk.StringVar(),
    "Age": tk.StringVar(),
    "Gender": tk.StringVar(),
}
for r, (lbl, var) in enumerate(post_vars.items()):
    ttk.Label(t_post, text=lbl).grid(row=r, column=0, sticky="w", padx=3, pady=2)
    ttk.Entry(t_post, textvariable=var, width=40).grid(
        row=r, column=1, sticky="ew", pady=2
    )

ttk.Label(t_post, text="Content*").grid(row=len(post_vars), column=0, sticky="nw")
content_txt = scrolledtext.ScrolledText(t_post, width=60, height=5, wrap="word")
content_txt.grid(row=len(post_vars), column=1, sticky="ew")

mult_v = tk.IntVar(); ver_v = tk.IntVar()
ttk.Checkbutton(t_post, text="Contains multimedia", variable=mult_v).grid(
    row=len(post_vars) + 1, column=0, sticky="w"
)
ttk.Checkbutton(t_post, text="Verified user", variable=ver_v).grid(
    row=len(post_vars) + 1, column=1, sticky="w"
)
t_post.columnconfigure(1, weight=1)


def add_post():
    try:
        likes = int(post_vars["Likes"].get() or 0)
        dislikes = int(post_vars["Dislikes"].get() or 0)
        age = int(post_vars["Age"].get()) if post_vars["Age"].get().isdigit() else None
        ptime = iso(post_vars["Post time (YYYY‑MM‑DD HH:MM:SS)*"].get())
    except ValueError as e:
        return messagebox.showerror("Bad input", str(e))

    payload = {
        "username": post_vars["Username*"].get().strip(),
        "social_media": post_vars["Social media*"].get().strip(),
        "post_time": ptime,
        "content": content_txt.get("1.0", "end").strip(),
        "city": post_vars["City"].get() or None,
        "state": post_vars["State"].get() or None,
        "country": post_vars["Country"].get() or None,
        "likes": likes,
        "dislikes": dislikes,
        "multimedia": bool(mult_v.get()),
        "media_url": post_vars["Media URL"].get() or None,
        "first_name": post_vars["First name"].get() or None,
        "last_name": post_vars["Last name"].get() or None,
        "birth_country": post_vars["Birth country"].get() or None,
        "residence_country": post_vars["Residence country"].get() or None,
        "age": age,
        "gender": post_vars["Gender"].get() or None,
        "verified": bool(ver_v.get()),
    }
    if not payload["username"] or not payload["social_media"] or not payload["content"]:
        return messagebox.showerror("Missing", "Starred fields are required")
    post("/add_post", payload, "Post added")


ttk.Button(t_post, text="Add Post", command=add_post).grid(
    row=len(post_vars) + 2, column=0, columnspan=2, pady=10
)

# ======================================================================
# TAB – Repost Post
# ======================================================================
t_repost = ttk.Frame(nb)
nb.add(t_repost, text="Repost")

# Dropdowns
selected_username = tk.StringVar()
selected_platform = tk.StringVar()
repost_time = tk.StringVar()

# Username dropdown
ttk.Label(t_repost, text="Select Username").grid(row=0, column=0, sticky="w", padx=5, pady=5)
username_dropdown = ttk.Combobox(t_repost, textvariable=selected_username, width=30, state="readonly")
username_dropdown.grid(row=0, column=1, padx=5, pady=5)

# Platform dropdown
ttk.Label(t_repost, text="Select Social Media").grid(row=1, column=0, sticky="w", padx=5, pady=5)
platform_dropdown = ttk.Combobox(t_repost, textvariable=selected_platform, width=30, state="readonly")
platform_dropdown.grid(row=1, column=1, padx=5, pady=5)

# Posts list
posts_listbox = tk.Listbox(t_repost, width=80, height=10)
posts_listbox.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

# Repost time
ttk.Label(t_repost, text="Repost Time (YYYY-MM-DD HH:MM:SS)").grid(row=3, column=0, padx=5, pady=5, sticky="w")
ttk.Entry(t_repost, textvariable=repost_time, width=30).grid(row=3, column=1, padx=5, pady=5)

def load_usernames():
    res = get("/list_usernames")
    if res:
        username_dropdown["values"] = res.get("usernames", [])

def load_platforms(*_):
    posts_listbox.delete(0, tk.END)
    selected_platform.set("")
    platform_dropdown["values"] = []
    res = get("/list_user_platforms", {"username": selected_username.get()})
    if res:
        platform_dropdown["values"] = res.get("platforms", [])

def load_posts(*_):
    posts_listbox.delete(0, tk.END)
    res = get("/list_user_posts", {
        "username": selected_username.get(),
        "platform": selected_platform.get()
    })
    if res:
        for p in res["posts"]:
            if p["type"] == "repost":
                tag = f"[Repost of ID {p['original_post_id']}]"
            else:
                tag = "[Original]"
            label = f"{p['id']} | {p['post_time']} | @{p['username']} | {tag} {p['content'][:50]}..."
            posts_listbox.insert(tk.END, label)
#
# Perform repost request
def perform_repost():
    selection = posts_listbox.curselection()
    if not selection:
        return messagebox.showerror("Missing", "Please select a post to repost.")

    pid = int(posts_listbox.get(selection[0]).split(" | ")[0])
    username = selected_username.get()
    time_str = repost_time.get().strip()

    if not username:
        return messagebox.showerror("Missing", "Please select a username.")
    if not selected_platform.get():
        return messagebox.showerror("Missing", "Please select a social media platform.")
    if not time_str:
        return messagebox.showerror("Missing", "Please enter a repost time.")

    # Validate datetime format
    try:
        datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return messagebox.showerror("Invalid Format", "Repost time must be in 'YYYY-MM-DD HH:MM:SS' format.")

    payload = {
        "original_post_id": pid,
        "reposter_username": username,
        "repost_time": time_str
    }

    try:
        response = requests.post(f"{API_URL}/repost", json=payload)
        if response.status_code == 201:
            messagebox.showinfo("Success", "Repost created successfully!")
            repost_time.set("")
            load_posts()  # Refresh the list to show the new repost
        elif response.status_code == 400:
            error_msg = response.json().get("status", "Bad request. Please check your input.")
            messagebox.showerror("Error", error_msg)
        else:
            messagebox.showerror("Server Error", f"Unexpected error: {response.text}")
    except requests.exceptions.ConnectionError:
        messagebox.showerror("Connection Error", "Could not connect to the server. Is it running?")
    except Exception as e:
        messagebox.showerror("Unexpected Error", str(e))

# Repost button
ttk.Button(t_repost, text="Repost", command=perform_repost).grid(row=4, column=0, columnspan=2, pady=10)

# Bind events
username_dropdown.bind("<<ComboboxSelected>>", load_platforms)
platform_dropdown.bind("<<ComboboxSelected>>", load_posts)

# Initial load
load_usernames()


# ======================================================================
# TAB 4 – Enter Results
# ======================================================================
# TAB – Unified Enter Results (Replace your t_enter block with this)
t_enter = ttk.Frame(nb)
nb.add(t_enter, text="Enter Results")

selected_project_id = tk.StringVar()
project_dropdown = ttk.Combobox(t_enter, textvariable=selected_project_id, width=40, state="readonly")
project_dropdown.grid(row=0, column=1, sticky="w", pady=5, padx=5)
ttk.Label(t_enter, text="Select Project*").grid(row=0, column=0, sticky="w", padx=5)

project_label = ttk.Label(t_enter, text="", font=("Segoe UI", 10, "italic"), foreground="gray")
project_label.grid(row=0, column=2, padx=10, sticky="w")

def update_project_label(*args):
    project_label.config(text=selected_project_id.get())

project_dropdown.bind("<<ComboboxSelected>>", lambda e: [load_posts_for_project(), update_project_label()])

select_all_var = tk.IntVar()
posts_checkbox_frame = ttk.LabelFrame(t_enter, text="Select Posts")
posts_checkbox_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

post_check_vars = []

def toggle_all():
    for var, _ in post_check_vars:
        var.set(select_all_var.get())
    on_checkbox_toggle()

def on_checkbox_toggle():
    if any(var.get() for var, _ in post_check_vars):
        results_frame.grid()
    else:
        results_frame.grid_remove()

ttk.Checkbutton(
    posts_checkbox_frame,
    text="Select All Posts",
    variable=select_all_var,
    command=toggle_all
).pack(anchor="w", pady=(0, 5))

def load_posts_for_project(*args):
    for cb in posts_checkbox_frame.winfo_children():
        cb.destroy()
    post_check_vars.clear()

    pid = selected_project_id.get().split(":")[0]
    if not pid.isdigit():
        return

    data = get("/query_project_analysis", {"project_id": int(pid)})
    if not data: return

    ttk.Checkbutton(
        posts_checkbox_frame,
        text="Select All Posts",
        variable=select_all_var,
        command=toggle_all
    ).pack(anchor="w", pady=(0, 5))

    for post in data.get("posts", []):
        var = tk.IntVar()
        cb = ttk.Checkbutton(
            posts_checkbox_frame,
            text=f"Post ID {post['id']} – {post['content'][:30]}",
            variable=var,
            command=on_checkbox_toggle
        )
        cb.pack(anchor="w")
        post_check_vars.append((var, post["id"]))

# ---- Results entry section (initially hidden) ----
# ---- Results entry section (initially hidden) ----
results_frame = ttk.LabelFrame(t_enter, text="Enter Analysis Results")
results_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
results_frame.grid_remove()

# Scrollable canvas inside frame
# Scrollable canvas inside frame with horizontal + vertical scroll
canvas = tk.Canvas(results_frame, height=160)
scroll_y = tk.Scrollbar(results_frame, orient="vertical", command=canvas.yview)
scroll_x = tk.Scrollbar(results_frame, orient="horizontal", command=canvas.xview)

entry_container = ttk.Frame(canvas)

entry_container.bind("<Configure>", lambda e: canvas.configure(
    scrollregion=canvas.bbox("all"),
    width=e.width
))
canvas.create_window((0, 0), window=entry_container, anchor="nw")

canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

canvas.grid(row=0, column=0, sticky="nsew")
scroll_y.grid(row=0, column=1, sticky="ns")
scroll_x.grid(row=1, column=0, sticky="ew")

results_frame.columnconfigure(0, weight=1)
results_frame.rowconfigure(0, weight=1)

pair_vars = []

def add_field_row():
    k = tk.StringVar()
    v = tk.StringVar()
    row = len(pair_vars)

    key_entry = ttk.Entry(entry_container, textvariable=k, width=20)
    val_entry = ttk.Entry(entry_container, textvariable=v, width=40)
    remove_btn = ttk.Button(entry_container, text="🗑", width=3)

    def remove_row():
        key_entry.destroy()
        val_entry.destroy()
        remove_btn.destroy()
        pair_vars.remove((k, v))

    remove_btn.config(command=remove_row)

    key_entry.grid(row=row, column=0, padx=2, pady=2)
    val_entry.grid(row=row, column=1, padx=2, pady=2)
    remove_btn.grid(row=row, column=2, padx=2, pady=2)

    pair_vars.append((k, v))


ttk.Button(results_frame, text="➕ Add Field", command=add_field_row).grid(row=1, column=0, columnspan=2, pady=(6, 4))

def save_results():
    if not selected_project_id.get():
        return messagebox.showerror("Missing", "Select a project first")

    project_id = int(selected_project_id.get().split(":")[0])
    selected_post_ids = [pid for var, pid in post_check_vars if var.get() == 1]

    if not selected_post_ids:
        return messagebox.showerror("Missing", "Select at least one post")

    results = {}
    seen_keys = set()

    for k_var, v_var in pair_vars:
        key = k_var.get().strip()
        value = v_var.get().strip()
        if key:
            if key in seen_keys:
                return messagebox.showerror("Duplicate Key", f"Field '{key}' is entered more than once.")
        results[key] = value
        seen_keys.add(key)

    if not results:
        return messagebox.showerror("Missing", "Enter at least one (field, value)")
    
    for post_id in selected_post_ids:
        payload = {
            "project_id": project_id,
            "post_id": post_id,
            "results": results
        }
        post("/enter_analysis_result", payload)

    # Show success as dialog box
    messagebox.showinfo("Saved", f"Saved results for {len(selected_post_ids)} post(s).")
    if not messagebox.askyesno("Confirm", "Do you want to clear the form now?"):
        return

    # Clear all fields
    for widget in entry_container.winfo_children():
        widget.destroy()
    pair_vars.clear()
    add_field_row()

    for var, _ in post_check_vars: var.set(0)
    select_all_var.set(0)
    results_frame.grid_remove()

ttk.Button(results_frame, text="💾 Save Results", command=save_results).grid(row=2, column=0, columnspan=2, pady=10)

# Add initial row
add_field_row()

def load_projects():
    try:
        res = requests.get("http://127.0.0.1:5000/list_projects")
        projects = res.json().get("projects", [])
        project_dropdown["values"] = [f"{p['id']}: {p['name']}" for p in projects]
    except Exception as e:
        print("Error loading projects:", e)

load_projects()

# ======================================================================
# TAB 5 – Search Posts
# ======================================================================
t_search = ttk.Frame(nb)
nb.add(t_search, text="Search Posts")

flt = {
    "Social media": tk.StringVar(),
    "From (YYYY‑MM‑DD HH:MM:SS)": tk.StringVar(),
    "To (YYYY‑MM‑DD HH:MM:SS)": tk.StringVar(),
    "Username": tk.StringVar(),
    "First name": tk.StringVar(),
    "Last name": tk.StringVar(),
}
for r, (lbl, var) in enumerate(flt.items()):
    ttk.Label(t_search, text=lbl).grid(row=r, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(t_search, textvariable=var, width=28).grid(row=r, column=1, sticky="ew")
t_search.columnconfigure(1, weight=1)

tree = ttk.Treeview(
    t_search,
    columns=("id", "media", "user", "time", "text", "exp"),
    show="headings",
    height=15,
)
for c, txt, w in [
    ("id", "ID", 50), ("media", "Platform", 90), ("user", "Username", 110),
    ("time", "Time", 130), ("text", "Text", 260), ("exp", "Experiment", 150)
]:
    tree.heading(c, text=txt); tree.column(c, width=w, anchor="w")
tree.grid(row=len(flt)+1, column=0, columnspan=2, sticky="nsew", pady=6)
t_search.rowconfigure(len(flt)+1, weight=1)
t_search.columnconfigure(1, weight=1)


def search_posts():
    p = {}
    if flt["Social media"].get(): p["social_media"] = flt["Social media"].get().strip()
    if flt["Username"].get(): p["username"] = flt["Username"].get().strip()
    if flt["First name"].get(): p["first_name"] = flt["First name"].get().strip()
    if flt["Last name"].get(): p["last_name"] = flt["Last name"].get().strip()
    if flt["From (YYYY‑MM‑DD HH:MM:SS)"].get() and flt["To (YYYY‑MM‑DD HH:MM:SS)"].get():
        p["from_time"] = flt["From (YYYY‑MM‑DD HH:MM:SS)"].get().strip()
        p["to_time"]   = flt["To (YYYY‑MM‑DD HH:MM:SS)"].get().strip()

    data = get("/search_post", p)
    if not data: return
    tree.delete(*tree.get_children())
    for exp, d in data["experiments"].items():
        for pst in d["posts"]:
            tree.insert("", "end", values=(
                pst["id"], pst["social_media"], pst["username"],
                pst["post_time"],
                (pst["text"][:45] + "…") if len(pst["text"]) > 45 else pst["text"],
                exp
            ))


ttk.Button(t_search, text="Search", command=search_posts).grid(
    row=len(flt), column=0, columnspan=2, pady=6
)

# ======================================================================
# TAB 6 – Experiment Details
# ======================================================================
t_exp = ttk.Frame(nb)
nb.add(t_exp, text="Experiment Details")

exp_name = tk.StringVar()
ttk.Label(t_exp, text="Experiment name*").grid(row=0, column=0, sticky="w", padx=4, pady=4)
ttk.Entry(t_exp, textvariable=exp_name, width=30).grid(row=0, column=1, sticky="ew", pady=4)
t_exp.columnconfigure(1, weight=1)

exp_tree = ttk.Treeview(
    t_exp, columns=("post","user","time","text","results"), show="headings", height=15
)
for c,txt,w in [
    ("post","Post ID",60),("user","User",100),("time","Time",130),
    ("text","Text",260),("results","Results",300)
]:
    exp_tree.heading(c, text=txt); exp_tree.column(c, width=w, anchor="w")
exp_tree.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=6)
t_exp.rowconfigure(2, weight=1); t_exp.columnconfigure(1, weight=1)


def load_exp():
    if not exp_name.get().strip():
        return messagebox.showerror("Missing","Enter name")
    data = get("/query_project_analysis", {"project_name": exp_name.get().strip()})
    if not data: return
    exp_tree.delete(*exp_tree.get_children())
    for p in data["posts"]:
        exp_tree.insert("", "end", values=(
            p["id"], p["username"], p["post_time"],
            (p["content"][:45]+"…") if len(p["content"])>45 else p["content"],
            json.dumps(p.get("results",{}), ensure_ascii=False)[:120]
        ))
    pct_text = "\n".join(f"{k}: {v}" for k,v in data["field_completion"].items())
    messagebox.showinfo("Field coverage", pct_text or "No fields yet")


ttk.Button(t_exp, text="Load", command=load_exp).grid(row=1, column=0, columnspan=2, pady=6)

# ======================================================================
# TAB 7 – Subset Experiments (CS7330)
# ======================================================================
t_combo = ttk.Frame(nb)
nb.add(t_combo, text="Subset Experiments")

cmb = {k: tk.StringVar() for k in flt}
for r,(lbl,var) in enumerate(cmb.items()):
    ttk.Label(t_combo, text=lbl).grid(row=r, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(t_combo, textvariable=var, width=28).grid(row=r, column=1, sticky="ew")
t_combo.columnconfigure(1, weight=1)

combo_tree = ttk.Treeview(
    t_combo, columns=("exp","post","field","value","pct"), show="headings", height=16
)
for c,txt,w in [
    ("exp","Experiment",140), ("post","Post",60), ("field","Field",120),
    ("value","Value",240), ("pct","% posts",90)
]:
    combo_tree.heading(c, text=txt); combo_tree.column(c, width=w, anchor="w")
combo_tree.grid(row=len(cmb)+2, column=0, columnspan=2, sticky="nsew", pady=6)
t_combo.rowconfigure(len(cmb)+2, weight=1); t_combo.columnconfigure(1, weight=1)


def run_combo():
    p={}
    if cmb["Social media"].get(): p["social_media"]=cmb["Social media"].get().strip()
    if cmb["Username"].get(): p["username"]=cmb["Username"].get().strip()
    if cmb["First name"].get(): p["first_name"]=cmb["First name"].get().strip()
    if cmb["Last name"].get(): p["last_name"]=cmb["Last name"].get().strip()
    if cmb["From (YYYY‑MM‑DD HH:MM:SS)"].get() and cmb["To (YYYY‑MM‑DD HH:MM:SS)"].get():
        p["from_time"]=cmb["From (YYYY‑MM‑DD HH:MM:SS)"].get().strip()
        p["to_time"]=cmb["To (YYYY‑MM‑DD HH:MM:SS)"].get().strip()

    data=get("/combo_post_to_experiment", p)
    if not data: return
    combo_tree.delete(*combo_tree.get_children())
    for exp,d in data["experiments"].items():
        pct=d["field_completion"]
        for pst in d["posts"]:
            for fld,val in pst["results"].items():
                combo_tree.insert("", "end", values=(
                    exp, pst["id"], fld,
                    (str(val)[:60]+"…") if len(str(val))>60 else val,
                    pct.get(fld,"")
                ))


ttk.Button(t_combo, text="Run query", command=run_combo).grid(
    row=len(cmb), column=0, columnspan=2, pady=6
)

# ----------------------------------------------------------------------
root.mainloop()