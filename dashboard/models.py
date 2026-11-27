from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum


class Customer(models.Model):
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name", "id"]

    def __str__(self):
        return self.full_name


class Device(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="devices"
    )
    device_type = models.CharField(max_length=60)
    brand = models.CharField(max_length=80)
    model = models.CharField(max_length=100)
    serial_number = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["brand", "model", "id"]

    def __str__(self):
        return f"{self.brand} {self.model}"


class RepairRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        DIAGNOSING = "Diagnosing", "Diagnosing"
        REPAIRING = "Repairing", "Repairing"
        READY = "Ready for Pickup", "Ready for Pickup"
        COMPLETED = "Completed", "Completed"

    device = models.ForeignKey(
        Device, on_delete=models.PROTECT, related_name="repairs"
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_repairs",
    )
    reported_problem = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    date_received = models.DateTimeField(auto_now_add=True)
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    final_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["-date_received"]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "Pending",
                        "Diagnosing",
                        "Repairing",
                        "Ready for Pickup",
                        "Completed",
                    ]
                ),
                name="repair_request_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(estimated_cost__gte=0),
                name="repair_estimated_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(final_cost__isnull=True) | Q(final_cost__gte=0),
                name="repair_final_cost_nonnegative",
            ),
        ]

    def __str__(self):
        return f"Repair #{self.pk} - {self.device}"

    @property
    def total_paid(self):
        # Use prefetched payments when a list page already loaded them,
        # so the list does not run one extra query per row.
        prefetched = getattr(self, "_prefetched_objects_cache", {}).get("payments")
        if prefetched is not None:
            return sum((p.amount for p in prefetched), Decimal("0.00"))
        return self.payments.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )

    @property
    def payment_status(self):
        if self.final_cost is not None and self.total_paid >= self.final_cost:
            return "Fully Paid"
        if self.total_paid == 0:
            return "Unpaid"
        return "Partially Paid"


class Diagnosis(models.Model):
    repair = models.ForeignKey(
        RepairRequest, on_delete=models.CASCADE, related_name="diagnoses"
    )
    findings = models.TextField()
    identified_issue = models.TextField()
    diagnosed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-diagnosed_at"]

    def __str__(self):
        return f"Diagnosis for repair #{self.repair_id}"


class RepairDetail(models.Model):
    repair = models.ForeignKey(
        RepairRequest, on_delete=models.CASCADE, related_name="work_entries"
    )
    work_performed = models.TextField()
    work_date = models.DateTimeField(auto_now_add=True)
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="repair_work",
    )

    class Meta:
        ordering = ["-work_date"]

    def __str__(self):
        return f"Work entry for repair #{self.repair_id}"


class Part(models.Model):
    part_name = models.CharField(max_length=120)
    part_code = models.CharField(max_length=80, unique=True)
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity_available = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["part_name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(unit_cost__gte=0),
                name="part_unit_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_available__gte=0),
                name="part_quantity_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.part_name} ({self.part_code})"


class RepairPart(models.Model):
    repair = models.ForeignKey(
        RepairRequest, on_delete=models.CASCADE, related_name="parts_used"
    )
    part = models.ForeignKey(
        Part, on_delete=models.PROTECT, related_name="repair_usages"
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost_at_use = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["repair", "part"], name="unique_part_per_repair"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1), name="repair_part_quantity_positive"
            ),
            models.CheckConstraint(
                condition=Q(unit_cost_at_use__gte=0),
                name="repair_part_cost_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.part} for repair #{self.repair_id}"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "Cash", "Cash"
        CARD = "Card", "Card (recorded)"
        OTHER = "Other", "Other"

    repair = models.ForeignKey(
        RepairRequest, on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_method = models.CharField(
        max_length=20, choices=Method.choices, default=Method.CASH
    )
    paid_at = models.DateTimeField(auto_now_add=True)
    reference_note = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ["-paid_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(payment_method__in=["Cash", "Card", "Other"]),
                name="payment_valid_method",
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="payment_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.amount} payment for repair #{self.repair_id}"


class Pickup(models.Model):
    repair = models.OneToOneField(
        RepairRequest, on_delete=models.PROTECT, related_name="pickup"
    )
    picked_up_by = models.CharField(max_length=120)
    pickup_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Pickup for repair #{self.repair_id}"