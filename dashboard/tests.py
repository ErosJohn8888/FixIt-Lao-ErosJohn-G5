from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser

from .models import (
    Customer,
    Device,
    Part,
    Payment,
    RepairRequest,
)


PASSWORD = "FixIT-Staff-Test-Password-58!"


class RepairWorkflowTests(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username="staff",
            email="staff@example.com",
            password=PASSWORD,
        )
        self.manager = CustomUser.objects.create_user(
            username="manager",
            email="manager@example.com",
            password=PASSWORD,
            role=CustomUser.Role.MANAGER,
        )
        self.customer = Customer.objects.create(
            full_name="Alex Customer",
            phone="555-0123",
            email="alex@example.com",
        )
        self.device = Device.objects.create(
            customer=self.customer,
            device_type="Phone",
            brand="Example",
            model="One",
            serial_number="SERIAL-001",
        )
        self.repair = RepairRequest.objects.create(
            device=self.device,
            received_by=self.staff,
            reported_problem="Screen is broken",
            estimated_cost=Decimal("100.00"),
            final_cost=Decimal("100.00"),
        )
        self.part = Part.objects.create(
            part_name="Display",
            part_code="DISP-1",
            unit_cost=Decimal("25.00"),
            quantity_available=5,
        )
        self.client.force_login(self.staff)

    def test_staff_dashboard_is_login_protected_and_shows_repair_summary(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FixIT Repair Management")
        self.assertContains(response, "Alex Customer")

        self.client.logout()
        response = self.client.get(reverse("customer_list"))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('customer_list')}"
        )

    def test_staff_can_create_and_search_customers(self):
        response = self.client.post(
            reverse("customer_add"),
            {
                "full_name": "Jamie New",
                "phone": "555-0100",
                "email": "jamie@example.com",
                "address": "",
            },
        )
        self.assertRedirects(response, reverse("customer_list"))
        self.assertTrue(Customer.objects.filter(full_name="Jamie New").exists())

        response = self.client.get(
            reverse("customer_list"), {"q": "Jamie"}
        )
        self.assertContains(response, "Jamie New")
        self.assertNotContains(response, "Alex Customer")

    def test_customer_with_device_cannot_be_deleted(self):
        response = self.client.post(
            reverse("customer_delete", args=[self.customer.pk]), follow=True
        )
        self.assertContains(response, "related devices or repair history")
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_duplicate_device_serial_is_rejected(self):
        response = self.client.post(
            reverse("device_add"),
            {
                "customer": self.customer.pk,
                "device_type": "Tablet",
                "brand": "Example",
                "model": "Two",
                "serial_number": "SERIAL-001",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Device with this Serial number already exists.")

    def test_repair_list_filters_by_status_and_customer(self):
        response = self.client.get(
            reverse("repair_list"),
            {
                "status": RepairRequest.Status.PENDING,
                "customer": self.customer.pk,
                "device": self.device.pk,
            },
        )
        self.assertContains(response, "Alex Customer")
        self.assertContains(response, f"#{self.repair.pk}")

    def test_diagnosis_and_work_are_recorded_in_repair_history(self):
        response = self.client.post(
            reverse("diagnosis_add", args=[self.repair.pk]),
            {"findings": "Display is cracked", "identified_issue": "Broken panel"},
        )
        self.assertRedirects(response, reverse("repair_detail", args=[self.repair.pk]))

        response = self.client.post(
            reverse("work_add", args=[self.repair.pk]),
            {"work_performed": "Replaced the display"},
        )
        self.assertRedirects(response, reverse("repair_detail", args=[self.repair.pk]))
        detail = self.client.get(reverse("repair_detail", args=[self.repair.pk]))
        self.assertContains(detail, "Broken panel")
        self.assertContains(detail, "Replaced the display")

    def test_repair_cannot_be_marked_ready_without_work(self):
        response = self.client.post(
            reverse("repair_edit", args=[self.repair.pk]),
            {
                "device": self.device.pk,
                "reported_problem": self.repair.reported_problem,
                "status": RepairRequest.Status.READY,
                "estimated_cost": "100.00",
                "final_cost": "100.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Record at least one repair work entry")

    def test_payment_balance_and_payment_status_are_consistent(self):
        response = self.client.post(
            reverse("payment_add", args=[self.repair.pk]),
            {"amount": "40.00", "payment_method": "Cash", "reference_note": ""},
        )
        self.assertRedirects(response, reverse("repair_detail", args=[self.repair.pk]))
        self.repair.refresh_from_db()
        self.assertEqual(self.repair.total_paid, Decimal("40.00"))
        self.assertEqual(self.repair.payment_status, "Partially Paid")

        response = self.client.post(
            reverse("payment_add", args=[self.repair.pk]),
            {"amount": "60.00", "payment_method": "Cash", "reference_note": ""},
        )
        self.assertRedirects(response, reverse("repair_detail", args=[self.repair.pk]))
        self.repair.refresh_from_db()
        self.assertEqual(self.repair.payment_status, "Fully Paid")

    def test_overpayment_is_rejected(self):
        response = self.client.post(
            reverse("payment_add", args=[self.repair.pk]),
            {"amount": "100.01", "payment_method": "Cash", "reference_note": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot exceed the remaining repair balance")
        self.assertFalse(Payment.objects.filter(repair=self.repair).exists())

    def test_final_cost_cannot_be_reduced_below_recorded_payments(self):
        Payment.objects.create(
            repair=self.repair,
            amount=Decimal("40.00"),
            payment_method=Payment.Method.CASH,
        )
        response = self.client.post(
            reverse("repair_edit", args=[self.repair.pk]),
            {
                "device": self.device.pk,
                "reported_problem": self.repair.reported_problem,
                "status": RepairRequest.Status.PENDING,
                "estimated_cost": "100.00",
                "final_cost": "30.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Final cost cannot be lower than payments")
        self.repair.refresh_from_db()
        self.assertEqual(self.repair.final_cost, Decimal("100.00"))

    def test_parts_usage_decrements_inventory_and_removal_restores_it(self):
        response = self.client.post(
            reverse("repair_part_add", args=[self.repair.pk]),
            {"part": self.part.pk, "quantity": "2"},
        )
        self.assertRedirects(response, reverse("repair_detail", args=[self.repair.pk]))
        self.part.refresh_from_db()
        self.assertEqual(self.part.quantity_available, 3)

        usage = self.repair.parts_used.get(part=self.part)
        response = self.client.post(
            reverse("repair_part_delete", args=[usage.pk]), follow=True
        )
        self.assertContains(response, "inventory restored")
        self.part.refresh_from_db()
        self.assertEqual(self.part.quantity_available, 5)

    def test_pickup_completes_only_ready_repair_with_work(self):
        response = self.client.post(
            reverse("pickup_add", args=[self.repair.pk]),
            {"picked_up_by": "Alex Customer", "notes": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ready for pickup")
        self.assertFalse(hasattr(self.repair, "pickup"))

        self.repair.work_entries.create(
            work_performed="Replaced display", staff=self.staff
        )
        self.repair.status = RepairRequest.Status.READY
        self.repair.save(update_fields=["status"])
        response = self.client.post(
            reverse("pickup_add", args=[self.repair.pk]),
            {"picked_up_by": "Alex Customer", "notes": "Device checked"},
        )
        self.assertRedirects(response, reverse("repair_detail", args=[self.repair.pk]))
        self.repair.refresh_from_db()
        self.assertEqual(self.repair.status, RepairRequest.Status.COMPLETED)
        self.assertEqual(self.repair.pickup.picked_up_by, "Alex Customer")

    def test_manager_can_see_report_but_staff_cannot(self):
        Payment.objects.create(
            repair=self.repair,
            amount=Decimal("40.00"),
            payment_method=Payment.Method.CASH,
        )
        self.assertEqual(self.client.get(reverse("reports")).status_code, 403)
        self.client.force_login(self.manager)
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Repair and payment report")
        self.assertContains(response, "$100.00")
        self.assertEqual(response.context["payment_total"], Decimal("40.00"))

    def test_manager_report_filters_by_date_and_status(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("reports"),
            {
                "status": RepairRequest.Status.PENDING,
                "start_date": "2020-01-01",
                "end_date": "2020-01-02",
            },
        )
        self.assertContains(response, "Repair requests")
        self.assertContains(response, "0</strong>")


class RoleRegistrationTests(TestCase):
    def test_public_registration_cannot_create_manager(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "selfpromoted",
                "email": "selfpromoted@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
                "role": CustomUser.Role.MANAGER,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            CustomUser.objects.get(username="selfpromoted").role,
            CustomUser.Role.STAFF,
        )
