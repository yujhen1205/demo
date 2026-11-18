from db import get_db_connection
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)

app.secret_key = "submission_system_secret"

# 測試帳號
users = {
    "author01": {
        "password": "Author2026!TryA9",
        "role": "author"
    },
    "editor01": {
        "password": "Editor2026!TryB7",
        "role": "editor"
    }
}
# 登入頁面
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        if username in users:
            if users[username]["password"] == password:
                if users[username]["role"] == role:

                    session["username"] = username
                    session["role"] = role

                    if role == "author":
                        return redirect(url_for("author_home"))

                    else:
                        return redirect(url_for("editor_home"))

        return "帳號、密碼或身分錯誤！ <a href='/'>重新登入</a>"

    return render_template("login.html")



# 作者首頁
@app.route("/author")
def author_home():

    if session.get("role") != "author":
        return redirect(url_for("login"))

    return render_template("author.html")




# 作者新增投稿
@app.route("/submit", methods=["GET", "POST"])
def submit():

    if session.get("role") != "author":
        return redirect(url_for("login"))

    if request.method == "POST":

        category = request.form["category"]
        title = request.form["title"]
        content = request.form["content"]

        conn = get_db_connection()

        try:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT user_id
                    FROM users
                    WHERE username = %s
                """, (session["username"],))

                user = cur.fetchone()

                if not user:
                    return "找不到作者帳號！"

                user_id = user[0]

                # 新增投稿資料
                cur.execute("""
                    INSERT INTO submissions
                    (user_id, category, title, content,
                     status, submitted_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (
                    user_id,
                    category,
                    title,
                    content,
                    "審查中"
                ))

            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"投稿失敗：{e}"

        finally:
            conn.close()

        return redirect(url_for("my_submissions"))

    return render_template("submit.html", form_data={})



# 作者編輯投稿及重新送交審查
@app.route("/edit_submission/<int:submission_id>", methods=["GET", "POST"])
def edit_submission(submission_id):

    if session.get("role") != "author":
        return redirect(url_for("login"))

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            # 確認稿件屬於目前登入的作者
            # 並且狀態是編輯中或已退稿
            cur.execute("""
                SELECT s.category, s.title, s.content, s.status
                FROM submissions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.submission_id = %s
                AND u.username = %s
                AND s.status IN ('編輯中', '已退稿')
            """, (
                submission_id,
                session["username"]
            ))

            submission = cur.fetchone()

            if not submission:
                return "找不到稿件，或目前狀態無法編輯！"

            if request.method == "POST":

                category = request.form["category"]
                title = request.form["title"]
                content = request.form["content"]

                action = request.form.get("action")

                # 儲存修改，但不重新送審
                if action == "save":

                    status = submission[3]

                # 儲存修改並重新送交編輯審查
                elif action == "submit":

                    status = "審查中"

                else:
                    return "無效的操作！"

                cur.execute("""
                    UPDATE submissions
                    SET category = %s,
                        title = %s,
                        content = %s,
                        status = %s
                    WHERE submission_id = %s
                    AND user_id = (
                        SELECT user_id
                        FROM users
                        WHERE username = %s
                    )
                    AND status IN ('編輯中', '已退稿')
                """, (
                    category,
                    title,
                    content,
                    status,
                    submission_id,
                    session["username"]
                ))

                if cur.rowcount == 0:
                    conn.rollback()
                    return "修改失敗，請重新確認稿件狀態！"

                conn.commit()

                return redirect(url_for("my_submissions"))

    finally:
        conn.close()

    return render_template(
        "edit_submission.html",
        submission=submission,
        submission_id=submission_id
    )
# 作者刪除編輯中或已退稿稿件
@app.route("/delete_submission/<int:submission_id>", methods=["POST"])
def delete_submission(submission_id):

    if session.get("role") != "author":
        return redirect(url_for("login"))

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                DELETE FROM submissions
                WHERE submission_id = %s
                AND user_id = (
                    SELECT user_id
                    FROM users
                    WHERE username = %s
                )
                AND status IN ('編輯中', '已退稿')
            """, (
                submission_id,
                session["username"]
            ))

            deleted = cur.rowcount

        conn.commit()

    finally:
        conn.close()

    if deleted == 0:
        return "刪除失敗！只能刪除自己編輯中或已退稿的稿件。"

    return redirect(url_for("my_submissions"))

# 作者查看投稿紀錄
@app.route("/my_submissions")
def my_submissions():

    if session.get("role") != "author":
        return redirect(url_for("login"))

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT submission_id, category, title, status, submitted_at
                FROM submissions
                WHERE user_id = (
                    SELECT user_id
                    FROM users
                    WHERE username = %s
                )
                ORDER BY submitted_at DESC
            """, (session["username"],))

            submissions = cur.fetchall()

    finally:
        conn.close()

    return render_template(
        "my_submissions.html",
        submissions=submissions
    )

# 編輯首頁
@app.route("/editor")
def editor_home():

    if session.get("role") != "editor":
        return redirect(url_for("login"))

    return render_template("editor.html")


# 編輯查看待審查稿件
@app.route("/pending_submissions")
def pending_submissions():

    if session.get("role") != "editor":
        return redirect(url_for("login"))

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    s.submission_id,
                    u.username,
                    s.category,
                    s.title,
                    s.status,
                    s.submitted_at
                FROM submissions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.status = %s
                ORDER BY s.submitted_at DESC
            """, ("審查中",))

            submissions = cur.fetchall()

    finally:
        conn.close()

    return render_template(
        "pending_submissions.html",
        submissions=submissions
    )


# 編輯管理所有投稿紀錄
@app.route("/all_submissions")
def all_submissions():

    if session.get("role") != "editor":
        return redirect(url_for("login"))

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    s.submission_id,
                    u.username,
                    s.category,
                    s.title,
                    s.status,
                    s.submitted_at
                FROM submissions s
                JOIN users u ON s.user_id = u.user_id
                ORDER BY s.submitted_at DESC
            """)

            submissions = cur.fetchall()

    finally:
        conn.close()

    return render_template(
        "all_submissions.html",
        submissions=submissions
    )



# 編輯查看稿件詳細內容
@app.route("/submission/<int:submission_id>")
def submission_detail(submission_id):

    if session.get("role") != "editor":
        return redirect(url_for("login"))

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    s.submission_id,
                    u.username,
                    s.category,
                    s.title,
                    s.content,
                    s.status,
                    s.submitted_at
                FROM submissions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.submission_id = %s
            """, (submission_id,))

            submission = cur.fetchone()

    finally:
        conn.close()

    if not submission:
        return "找不到這篇稿件！"

    return render_template(
        "submission_detail.html",
        submission=submission
    )



# 編輯審查稿件
@app.route("/review/<int:submission_id>", methods=["POST"])
def review_submission(submission_id):

    if session.get("role") != "editor":
        return redirect(url_for("login"))

    status = request.form["status"]

    if status not in ["審查中", "已通過", "已退稿"]:
        return "無效的審查狀態！"

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                UPDATE submissions
                SET status = %s
                WHERE submission_id = %s
            """, (status, submission_id))

        conn.commit()

    finally:
        conn.close()

    return redirect(url_for(
        "submission_detail",
        submission_id=submission_id
    ))


# 登出
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

@app.route("/test_db")
def test_db():
    try:
        conn = get_db_connection()
        conn.close()
        return "PostgreSQL 連線成功！"
    except Exception as e:
        return f"資料庫連線失敗：{e}"
if __name__ == "__main__":
    app.run(debug=True)