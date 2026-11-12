from locust import HttpUser, task, between


class DatingAppUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def get_states(self):
        self.client.get("/states/")
