from clients_management import Client


class plan:
    Clients_progress = {}

    def __init__(self, client: Client, all_tasks=None):
        self.client = client
        self.Client_name = client.name
        self.all_tasks = all_tasks if all_tasks is not None else []
        self.pending_tasks = list(self.all_tasks)
        self.progress = 0

    def refresh_progress(self):
        if not self.all_tasks:
            self.progress = 100
            return self.progress

        remaining_tasks = len(self.pending_tasks)
        completed_tasks = len(self.all_tasks) - remaining_tasks
        self.progress = round((completed_tasks / len(self.all_tasks)) * 100)
        return self.progress

    def add_pending_task(self, task):
        self.all_tasks.append(task)
        self.pending_tasks.append(task)
        self.refresh_progress()
        self.update_clients_progress()

    def complete_task(self, task):
        if task in self.pending_tasks:
            self.pending_tasks.remove(task)
        self.refresh_progress()
        self.update_clients_progress()

    def to_dict(self):
        return {
            "client_name": self.Client_name,
            "progress": self.progress,
            "pending_tasks": self.pending_tasks,
            "all_tasks": self.all_tasks,
        }

    def update_clients_progress(self):
        self.refresh_progress()
        plan.Clients_progress[self.client.name] = self.to_dict()

    def progress_color(self):
        width = 30
        filled = int((self.progress / 100) * width)
        bar = "█" * filled + " " * (width - filled)
        print(f"|{bar}| {self.progress}%")
        print(f"Pending tasks: {len(self.pending_tasks)}")


client1 = Client("Ali", "123456", "Marketing")
plan1 = plan(client1, all_tasks=["task1", "task2", "task3", "task4", "task5"])
plan1.pending_tasks = ["task1", "task2", "task3"]
plan1.refresh_progress()
plan1.update_clients_progress()
print(plan.Clients_progress)
plan1.progress_color()