import sys
import io
import contextlib
from itertools import cycle
import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

status_lst = ["cancelled", "completed", "in_progress", "pending"]
priority_lst = ["high", "low", "medium"]


def get_task_list():
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        import this
    text = f.getvalue()
    status_cycle = cycle(status_lst)
    priority_cycle = cycle(priority_lst)
    tasks_lst = []
    num = 0
    for line in text.splitlines():
        if not line:
            continue
        num += 1
        tasks_lst.append({
            "id": num,
            "title": "Zen of Python",
            "description": line,
            "status": next(status_cycle),
            "priority": next(priority_cycle),
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "deleted_at": None,
        })
    return tasks_lst


tasks_lst = get_task_list()


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def validate_status(status: str) -> tuple:
    """Проверка статуса"""
    if status not in status_lst:
        return False, "Поле `status` невалидно"
    return True, None


def validate_priority(priority: str) -> tuple:
    """Проверка приоритета"""
    if priority not in priority_lst:
        return False, "Поле `priority` невалидно"
    return True, None


def get_task_by_id(task_id: int) -> dict | None:
    """Найти задачу по ID"""
    for task in tasks_lst:
        if task["id"] == task_id:
            return task
    return None


def safe_sort_key(task: dict, field: str):
    """Безопасная сортировка (обработка None)"""
    value = task.get(field)
    if value is None:
        if field in ("created_at", "updated_at", "deleted_at"):
            return datetime.datetime.min
        return ""
    return value


def parse_offset(offset_str: str) -> int:
    """Преобразование offset в число"""
    try:
        offset = int(offset_str)
        return max(offset, 0)
    except (ValueError, TypeError):
        return 0


# ========== ЭНДПОИНТЫ API ==========

@app.route("/api/v1/tasks", methods=["GET"])
def get_tasks():
    """GET /api/v1/tasks - получить список задач"""
    query = request.args.get("query", "").strip()
    order = request.args.get("order", "id")
    offset = parse_offset(request.args.get("offset", 0))

    tasks = tasks_lst[:]

    # Фильтрация по поисковому запросу
    if query:
        query_lower = query.lower()
        tasks = [
            task for task in tasks
            if query_lower in task["title"].lower()
               or query_lower in task["description"].lower()
        ]

    # Сортировка
    reverse = False
    sort_field = order
    if order.startswith("-"):
        sort_field = order[1:]
        reverse = True

    if tasks and sort_field not in tasks[0]:
        sort_field = "id"

    tasks.sort(key=lambda t: safe_sort_key(t, sort_field), reverse=reverse)

    # Пагинация (не более 10 элементов)
    tasks = tasks[offset:offset + 10]

    return jsonify({"tasks": tasks})


@app.route("/api/v1/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    """GET /api/v1/tasks/<id> - получить задачу по ID"""
    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "Задача не найдена"}), 404

    task = get_task_by_id(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404
    return jsonify(task)


@app.route("/api/v1/tasks", methods=["POST"])
def create_task():
    """POST /api/v1/tasks - создать новую задачу"""
    data = request.get_json()

    if data is None or data == {}:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    if "title" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `title`"}), 400
    if "description" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `description`"}), 400

    title = data["title"]
    description = data["description"]
    status = data.get("status", "pending")
    priority = data.get("priority", "medium")

    valid, err_msg = validate_status(status)
    if not valid:
        return jsonify({"error": err_msg}), 400

    valid, err_msg = validate_priority(priority)
    if not valid:
        return jsonify({"error": err_msg}), 400

    new_id = max((task["id"] for task in tasks_lst), default=0) + 1
    now = datetime.datetime.now().isoformat()

    new_task = {
        "id": new_id,
        "title": title,
        "description": description,
        "status": status,
        "priority": priority,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }

    tasks_lst.append(new_task)
    return jsonify(new_task), 200


@app.route("/api/v1/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    """DELETE /api/v1/tasks/<id> - мягкое удаление задачи"""
    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "Задача не найдена"}), 404

    task = get_task_by_id(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404

    task["status"] = "cancelled"
    task["deleted_at"] = datetime.datetime.now().isoformat()
    task["updated_at"] = datetime.datetime.now().isoformat()
    return jsonify(task), 200


@app.route("/api/v1/tasks/<task_id>", methods=["PATCH"])
def update_task(task_id):
    """PATCH /api/v1/tasks/<id> - частичное обновление задачи"""
    data = request.get_json()

    if data is None or data == {}:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "Задача не найдена"}), 404

    task = get_task_by_id(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404

    if "status" in data:
        valid, err_msg = validate_status(data["status"])
        if not valid:
            return jsonify({"error": err_msg}), 400

    if "priority" in data:
        valid, err_msg = validate_priority(data["priority"])
        if not valid:
            return jsonify({"error": err_msg}), 400

    allowed_fields = {"title", "description", "status", "priority"}
    for field in allowed_fields:
        if field in data:
            task[field] = data[field]

    task["updated_at"] = datetime.datetime.now().isoformat()
    return jsonify(task), 200


# ========== ЗАПУСК ==========
if __name__ == "__main__":
    app.run(debug=True, port=5444)
