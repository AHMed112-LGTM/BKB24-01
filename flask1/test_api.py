import requests
import json

BASE = "http://127.0.0.1:5444/api/v1/tasks"

print("=" * 50)
print("ТЕСТИРОВАНИЕ API")
print("=" * 50)

# 1. GET - список задач
print("\n1. GET /api/v1/tasks - список задач")
resp = requests.get(BASE)
print(f"Статус: {resp.status_code}")
data = resp.json()
print(f"Получено задач: {len(data['tasks'])}")
for task in data['tasks'][:3]:
    print(f"  - {task['id']}: {task['title']} [{task['status']}]")

# 2. GET - одна задача
print("\n2. GET /api/v1/tasks/1 - задача по ID")
resp = requests.get(f"{BASE}/1")
print(f"Статус: {resp.status_code}")
print(f"Задача: {resp.json()['title']}")

# 3. GET с поиском и сортировкой
print("\n3. GET /api/v1/tasks?query=never&order=-id - поиск")
resp = requests.get(f"{BASE}?query=never&order=-id")
print(f"Статус: {resp.status_code}")
data = resp.json()
print(f"Найдено: {len(data['tasks'])} задач")
for task in data['tasks']:
    print(f"  - ID {task['id']}: ...{task['description'][:30]}...")

# 4. POST - создать задачу
print("\n4. POST /api/v1/tasks - создание задачи")
new_task = {"title": "Новая задача", "description": "Описание задачи"}
resp = requests.post(BASE, json=new_task)
print(f"Статус: {resp.status_code}")
print(f"Создана задача с ID: {resp.json()['id']}")

# 5. PATCH - обновить задачу
print("\n5. PATCH /api/v1/tasks/1 - обновление статуса")
update = {"status": "completed"}
resp = requests.patch(f"{BASE}/1", json=update)
print(f"Статус: {resp.status_code}")
print(f"Новый статус: {resp.json()['status']}")

# 6. DELETE - мягкое удаление
print("\n6. DELETE /api/v1/tasks/2 - удаление задачи")
resp = requests.delete(f"{BASE}/2")
print(f"Статус: {resp.status_code}")
print(f"Статус задачи после удаления: {resp.json()['status']}")
print(f"deleted_at: {resp.json()['deleted_at']}")

# 7. GET несуществующей задачи
print("\n7. GET /api/v1/tasks/999 - несуществующая задача")
resp = requests.get(f"{BASE}/999")
print(f"Статус: {resp.status_code}")
print(f"Ошибка: {resp.json()['error']}")

print("\n" + "=" * 50)
print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("=" * 50)