"""Order API HTTP behaviour."""

from __future__ import annotations

import unittest

import order_api


class OrderApiTests(unittest.TestCase):
    def setUp(self) -> None:
        order_api.reset_store()
        self.client = order_api.app.test_client()

    def test_create_get_and_list(self) -> None:
        created = self.client.post("/orders", json={"item": "notebook", "quantity": 2})
        self.assertEqual(created.status_code, 201)
        body = created.get_json()
        self.assertEqual(body, {"id": 1, "item": "notebook", "quantity": 2, "status": "created"})

        fetched = self.client.get("/orders/1")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["item"], "notebook")

        listed = self.client.get("/orders")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()), 1)

    def test_ids_are_incremental(self) -> None:
        self.client.post("/orders", json={"item": "pen", "quantity": 1})
        second = self.client.post("/orders", json={"item": "pencil", "quantity": 3})
        self.assertEqual(second.get_json()["id"], 2)

    def test_quantity_must_be_positive(self) -> None:
        response = self.client.post("/orders", json={"item": "pen", "quantity": 0})
        self.assertEqual(response.status_code, 400)
        self.assertIn("quantity", response.get_json()["error"])

    def test_missing_item_is_rejected(self) -> None:
        response = self.client.post("/orders", json={"quantity": 1})
        self.assertEqual(response.status_code, 400)

    def test_unknown_order_is_404(self) -> None:
        response = self.client.get("/orders/9")
        self.assertEqual(response.status_code, 404)

    def test_non_json_is_415(self) -> None:
        response = self.client.post("/orders", data="item=pen", content_type="text/plain")
        self.assertEqual(response.status_code, 415)

    def test_gateway_prefix_uses_the_same_store(self) -> None:
        created = self.client.post("/api/orders", json={"item": "bag", "quantity": 1})
        self.assertEqual(created.status_code, 201)
        fetched = self.client.get("/orders/1")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["item"], "bag")


if __name__ == "__main__":
    unittest.main()
