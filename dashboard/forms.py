from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from accounts.validators import validate_phone

from .models import (
    Customer,
    Device,
    Diagnosis,
    Part,
    Payment,
    Pickup,
    RepairDetail,
    RepairPart,
    RepairRequest,
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-check-input"
                if isinstance(field.widget, forms.CheckboxInput)
                else "form-control"
            )


class CustomerForm(StyledModelForm):
    class Meta:
        model = Customer
        fields = ["full_name", "phone", "email", "address"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}

    def clean_full_name(self):
        name = self.cleaned_data["full_name"].strip()
        if len(name) < 2:
            raise ValidationError("Enter the customer's full name.")
        return name

    def clean_phone(self):
        return validate_phone(self.cleaned_data["phone"])


class DeviceForm(StyledModelForm):
    class Meta:
        model = Device
        fields = [
            "customer",
            "device_type",
            "brand",
            "model",
            "serial_number",
        ]

    def clean_serial_number(self):
        serial = (self.cleaned_data.get("serial_number") or "").strip()
        if not serial:
            return None
        duplicates = Device.objects.filter(serial_number__iexact=serial)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise ValidationError("Device with this Serial number already exists.")
        return serial


class RepairRequestForm(StyledModelForm):
    class Meta:
        model = RepairRequest
        fields = ["device", "reported_problem", "status", "estimated_cost", "final_cost"]
        widgets = {"reported_problem": forms.Textarea(attrs={"rows": 4})}

    def clean_reported_problem(self):
        problem = self.cleaned_data["reported_problem"].strip()
        if len(problem) < 5:
            raise ValidationError("Describe the problem in at least 5 characters.")
        return problem

    def clean_final_cost(self):
        final_cost = self.cleaned_data["final_cost"]
        if self.instance.pk:
            paid = self.instance.total_paid
            if paid and (final_cost is None or final_cost < paid):
                raise ValidationError(
                    "Final cost cannot be lower than payments already recorded."
                )
        return final_cost

    def clean_status(self):
        status = self.cleaned_data["status"]
        if status == RepairRequest.Status.READY:
            has_work = self.instance.pk and self.instance.work_entries.exists()
            if not has_work:
                raise ValidationError(
                    "Record at least one repair work entry before marking this "
                    "repair ready for pickup."
                )
        has_pickup = bool(self.instance.pk and hasattr(self.instance, "pickup"))
        if status == RepairRequest.Status.COMPLETED and not has_pickup:
            raise ValidationError(
                "Use the pickup action to complete and release this repair."
            )
        if has_pickup and status != RepairRequest.Status.COMPLETED:
            raise ValidationError(
                "This repair was already released. Undo the pickup first to "
                "change its status."
            )
        return status


class PartForm(StyledModelForm):
    class Meta:
        model = Part
        fields = ["part_name", "part_code", "unit_cost", "quantity_available"]

    def clean_part_code(self):
        code = self.cleaned_data["part_code"].strip().upper()
        duplicates = Part.objects.filter(part_code__iexact=code)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise ValidationError("A part with this code already exists.")
        return code


class DiagnosisForm(StyledModelForm):
    class Meta:
        model = Diagnosis
        fields = ["findings", "identified_issue"]
        widgets = {
            "findings": forms.Textarea(attrs={"rows": 4}),
            "identified_issue": forms.Textarea(attrs={"rows": 3}),
        }


class RepairDetailForm(StyledModelForm):
    class Meta:
        model = RepairDetail
        fields = ["work_performed"]
        widgets = {"work_performed": forms.Textarea(attrs={"rows": 4})}


class RepairPartForm(StyledModelForm):
    class Meta:
        model = RepairPart
        fields = ["part", "quantity"]

    def clean(self):
        cleaned_data = super().clean()
        part = cleaned_data.get("part")
        quantity = cleaned_data.get("quantity")
        if part and quantity:
            available = part.quantity_available
            if self.instance.pk and self.instance.part_id == part.pk:
                available += self.instance.quantity
            if quantity > available:
                self.add_error("quantity", "Not enough inventory is available.")
        return cleaned_data


class PaymentForm(StyledModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "payment_method", "reference_note"]

    def __init__(self, *args, repair, **kwargs):
        self.repair = repair
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if self.repair.final_cost is None:
            raise ValidationError(
                "Set the final repair cost before recording a payment."
            )
        paid = self.repair.total_paid
        if self.instance.pk:
            paid -= self.instance.amount
        if amount + paid > self.repair.final_cost:
            raise ValidationError(
                "The payment cannot exceed the remaining repair balance."
            )
        if amount <= Decimal("0.00"):
            raise ValidationError("Payment amount must be greater than zero.")
        return amount


class PickupForm(StyledModelForm):
    class Meta:
        model = Pickup
        fields = ["picked_up_by", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def clean_picked_up_by(self):
        name = self.cleaned_data["picked_up_by"].strip()
        if len(name) < 2:
            raise ValidationError("Enter the name of the person collecting the device.")
        return name


class RepairFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses"), *RepairRequest.Status.choices],
    )
    start_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be before start date.")
        return cleaned_data