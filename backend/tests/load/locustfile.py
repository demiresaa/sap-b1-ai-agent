"""Locust load testi.

Çalıştır:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 -t 5m
"""
from __future__ import annotations

import random

from locust import HttpUser, between, task

CREDENTIALS = {"email": "operator@test.local", "password": "password123"}


class OperatorUser(HttpUser):
    wait_time = between(2, 6)
    token: str | None = None

    def on_start(self) -> None:
        resp = self.client.post("/api/auth/login", json=CREDENTIALS)
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(5)
    def list_documents(self) -> None:
        self.client.get("/api/documents", headers=self._headers(), name="GET /documents")

    @task(2)
    def search_business_partners(self) -> None:
        q = random.choice(["Ali", "Mert", "AŞ", "Ltd", "Karpuz"])
        self.client.get(
            "/api/sap/business-partners",
            params={"search": q, "top": 20},
            headers=self._headers(),
            name="GET /sap/business-partners?search=*",
        )

    @task(2)
    def search_items(self) -> None:
        q = random.choice(["vana", "kablo", "boru", "civata"])
        self.client.get(
            "/api/sap/items",
            params={"search": q, "top": 20},
            headers=self._headers(),
            name="GET /sap/items?search=*",
        )

    @task(1)
    def me(self) -> None:
        self.client.get("/api/auth/me", headers=self._headers())
