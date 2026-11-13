from decimal import Decimal
from functools import reduce
from operator import or_

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.models import CustomUser

from .forms import (
    CustomerForm,
    DeviceForm,
    DiagnosisForm,
    PartForm,
    PaymentForm,
    PickupForm,
    RepairFilterForm,
    RepairDetailForm,
    RepairPartForm,
    RepairRequestForm,
)
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


class StaffRequiredMixin(LoginRequiredMixin):
    login_url = "login"


class ManagerRequiredMixin(StaffRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.role == CustomUser.Role.MANAGER
            or self.request.user.is_superuser
        )


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repairs = RepairRequest.objects.all()
        context["repair_count"] = repairs.count()
        context["pending_count"] = repairs.filter(
            status=RepairRequest.Status.PENDING
        ).count()
        context["active_count"] = repairs.filter(
            status__in=[
                RepairRequest.Status.DIAGNOSING,
                RepairRequest.Status.REPAIRING,
            ]
        ).count()
        context["ready_count"] = repairs.filter(
            status=RepairRequest.Status.READY
        ).count()
        context["recent_repairs"] = repairs.select_related(
            "device__customer", "received_by"
        )[:8]
        context["payment_total"] = (
            Payment.objects.aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        context["is_manager"] = (
            self.request.user.role == CustomUser.Role.MANAGER
            or self.request.user.is_superuser
        )
        return context


class RecordListView(StaffRequiredMixin, ListView):
    template_name = "dashboard/record_list.html"
    paginate_by = 25
    title = ""
    add_url = ""
    list_url = ""
    search_fields = ()
    search_placeholder = "Search"

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("q", "").strip()
        if search and self.search_fields:
            queryset = queryset.filter(
                reduce(or_, (Q(**{f"{field}__icontains": search}) for field in self.search_fields))
            )
        return queryset

    def get_context_data(self, **kwargs):
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context = super().get_context_data(**kwargs)
        context.update(
            title=self.title,
            list_kind=self.list_kind,
            add_url=self.add_url,
            list_url=self.list_url,
            search_placeholder=self.search_placeholder,
            search_value=self.request.GET.get("q", ""),
            query_params=query_params.urlencode(),
        )
        return context


class CustomerListView(RecordListView):
    model = Customer
    title = "Customers"
    list_kind = "customers"
    add_url = "customer_add"
    list_url = "customer_list"
    search_fields = ("full_name", "phone", "email")


class CustomerCreateView(StaffRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "dashboard/record_form.html"
    success_url = reverse_lazy("customer_list")
    extra_context = {
        "title": "Add customer",
        "cancel_url": reverse_lazy("customer_list"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Customer added.")
        return super().form_valid(form)


class CustomerUpdateView(StaffRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "dashboard/record_form.html"
    success_url = reverse_lazy("customer_list")
    extra_context = {
        "title": "Edit customer",
        "cancel_url": reverse_lazy("customer_list"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Customer updated.")
        return super().form_valid(form)


class DeviceListView(RecordListView):
    model = Device
    title = "Devices"
    list_kind = "devices"
    add_url = "device_add"
    list_url = "device_list"
    search_fields = (
        "customer__full_name",
        "customer__phone",
        "device_type",
        "brand",
        "model",
        "serial_number",
    )

    def get_queryset(self):
        return super().get_queryset().select_related("customer")


class DeviceCreateView(StaffRequiredMixin, CreateView):
    model = Device
    form_class = DeviceForm
    template_name = "dashboard/record_form.html"
    success_url = reverse_lazy("device_list")
    extra_context = {
        "title": "Register device",
        "cancel_url": reverse_lazy("device_list"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Device registered.")
        return super().form_valid(form)


class DeviceUpdateView(StaffRequiredMixin, UpdateView):
    model = Device
    form_class = DeviceForm
    template_name = "dashboard/record_form.html"
    success_url = reverse_lazy("device_list")
    extra_context = {
        "title": "Edit device",
        "cancel_url": reverse_lazy("device_list"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Device updated.")
        return super().form_valid(form)


class RepairListView(RecordListView):
    model = RepairRequest
    title = "Repair requests"
    list_kind = "repairs"
    add_url = "repair_add"
    list_url = "repair_list"
    search_fields = (
        "device__customer__full_name",
        "device__customer__phone",
        "device__device_type",
        "device__brand",
        "device__model",
        "device__serial_number",
        "reported_problem",
    )
    search_placeholder = "Customer, device, serial number, or issue"

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "device__customer", "received_by"
        )
        filter_form = RepairFilterForm(self.request.GET)
        if filter_form.is_valid():
            status = filter_form.cleaned_data["status"]
            if status:
                queryset = queryset.filter(status=status)
            start = filter_form.cleaned_data["start_date"]
            end = filter_form.cleaned_data["end_date"]
            if start:
                queryset = queryset.filter(date_received__date__gte=start)
            if end:
                queryset = queryset.filter(date_received__date__lte=end)
        customer_id = self.request.GET.get("customer", "")
        if customer_id.isdigit():
            queryset = queryset.filter(device__customer_id=customer_id)
        device_id = self.request.GET.get("device", "")
        if device_id.isdigit():
            queryset = queryset.filter(device_id=device_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = RepairFilterForm(self.request.GET or None)
        context["customers"] = Customer.objects.order_by("full_name")
        context["devices"] = Device.objects.select_related("customer").order_by(
            "brand", "model"
        )
        context["filters"] = {
            "customer": self.request.GET.get("customer", ""),
            "device": self.request.GET.get("device", ""),
        }
        return context


class RepairCreateView(StaffRequiredMixin, CreateView):
    model = RepairRequest
    form_class = RepairRequestForm
    template_name = "dashboard/record_form.html"
    extra_context = {
        "title": "Create repair request",
        "cancel_url": reverse_lazy("repair_list"),
    }

    def form_valid(self, form):
        form.instance.received_by = self.request.user
        messages.success(self.request, "Repair request created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("repair_detail", kwargs={"pk": self.object.pk})


class RepairUpdateView(StaffRequiredMixin, UpdateView):
    model = RepairRequest
    form_class = RepairRequestForm
    template_name = "dashboard/record_form.html"
    extra_context = {
        "title": "Edit repair request",
        "cancel_url": reverse_lazy("repair_list"),
    }

    def form_valid(self, form):
        with transaction.atomic():
            repair = RepairRequest.objects.select_for_update().get(pk=self.object.pk)
            final_cost = form.cleaned_data["final_cost"]
            if repair.total_paid and (
                final_cost is None or final_cost < repair.total_paid
            ):
                form.add_error(
                    "final_cost",
                    "Final cost cannot be lower than payments already recorded.",
                )
                return self.form_invalid(form)
            response = super().form_valid(form)
        messages.success(self.request, "Repair request updated.")
        return response

    def get_success_url(self):
        return reverse("repair_detail", kwargs={"pk": self.object.pk})


class PartListView(RecordListView):
    model = Part
    title = "Parts inventory"
    list_kind = "parts"
    add_url = "part_add"
    list_url = "part_list"
    search_fields = ("part_name", "part_code")


class PartCreateView(StaffRequiredMixin, CreateView):
    model = Part
    form_class = PartForm
    template_name = "dashboard/record_form.html"
    success_url = reverse_lazy("part_list")
    extra_context = {"title": "Add part", "cancel_url": reverse_lazy("part_list")}

    def form_valid(self, form):
        messages.success(self.request, "Part added to inventory.")
        return super().form_valid(form)


class PartUpdateView(StaffRequiredMixin, UpdateView):
    model = Part
    form_class = PartForm
    template_name = "dashboard/record_form.html"
    success_url = reverse_lazy("part_list")
    extra_context = {
        "title": "Edit part",
        "cancel_url": reverse_lazy("part_list"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Part updated.")
        return super().form_valid(form)


class RepairDetailView(StaffRequiredMixin, DetailView):
    model = RepairRequest
    template_name = "dashboard/repair_detail.html"
    queryset = RepairRequest.objects.select_related(
        "device__customer", "received_by"
    ).prefetch_related(
        "diagnoses", "work_entries__staff", "parts_used__part", "payments"
    )


class RepairChildCreateView(StaffRequiredMixin, CreateView):
    template_name = "dashboard/record_form.html"
    repair_id_url_kwarg = "repair_id"

    def get_repair(self):
        return get_object_or_404(
            RepairRequest, pk=self.kwargs[self.repair_id_url_kwarg]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["cancel_url"] = reverse(
            "repair_detail", kwargs={"pk": self.kwargs[self.repair_id_url_kwarg]}
        )
        return context

    def get_success_url(self):
        return reverse(
            "repair_detail", kwargs={"pk": self.kwargs[self.repair_id_url_kwarg]}
        )


class DiagnosisCreateView(RepairChildCreateView):
    model = Diagnosis
    form_class = DiagnosisForm
    title = "Add diagnosis"

    def form_valid(self, form):
        form.instance.repair = self.get_repair()
        messages.success(self.request, "Diagnosis recorded.")
        return super().form_valid(form)


class RepairDetailCreateView(RepairChildCreateView):
    model = RepairDetail
    form_class = RepairDetailForm
    title = "Record repair work"

    def form_valid(self, form):
        form.instance.repair = self.get_repair()
        form.instance.staff = self.request.user
        messages.success(self.request, "Repair work recorded.")
        return super().form_valid(form)


class PaymentCreateView(RepairChildCreateView):
    model = Payment
    form_class = PaymentForm
    title = "Record payment"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["repair"] = self.get_repair()
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                repair = RepairRequest.objects.select_for_update().get(
                    pk=self.kwargs["repair_id"]
                )
                amount = form.cleaned_data["amount"]
                remaining = (repair.final_cost or Decimal("0.00")) - repair.total_paid
                if repair.final_cost is None or amount > remaining:
                    form.add_error(
                        "amount", "This amount exceeds the remaining repair balance."
                    )
                    return self.form_invalid(form)
                form.instance.repair = repair
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "The payment could not be recorded. Please retry.")
            return self.form_invalid(form)
        messages.success(self.request, "Payment recorded.")
        return response


class RepairPartCreateView(RepairChildCreateView):
    model = RepairPart
    form_class = RepairPartForm
    title = "Record part usage"

    def form_valid(self, form):
        try:
            with transaction.atomic():
                part = Part.objects.select_for_update().get(
                    pk=form.cleaned_data["part"].pk
                )
                quantity = form.cleaned_data["quantity"]
                if quantity > part.quantity_available:
                    form.add_error("quantity", "Not enough inventory is available.")
                    return self.form_invalid(form)
                if RepairPart.objects.filter(
                    repair_id=self.kwargs["repair_id"], part=part
                ).exists():
                    form.add_error("part", "This part is already listed for this repair.")
                    return self.form_invalid(form)
                form.instance.repair = self.get_repair()
                form.instance.part = part
                form.instance.unit_cost_at_use = part.unit_cost
                response = super().form_valid(form)
                part.quantity_available -= quantity
                part.save(update_fields=["quantity_available"])
        except IntegrityError:
            form.add_error(None, "The part usage could not be recorded. Please retry.")
            return self.form_invalid(form)
        messages.success(self.request, "Part usage recorded and inventory updated.")
        return response


class PickupCreateView(RepairChildCreateView):
    model = Pickup
    form_class = PickupForm
    title = "Record device pickup"

    def form_valid(self, form):
        try:
            with transaction.atomic():
                repair = RepairRequest.objects.select_for_update().get(
                    pk=self.kwargs["repair_id"]
                )
                if repair.status != RepairRequest.Status.READY:
                    form.add_error(
                        None, "A repair must be ready for pickup before release."
                    )
                    return self.form_invalid(form)
                if not repair.work_entries.exists():
                    form.add_error(None, "Record repair work before releasing the device.")
                    return self.form_invalid(form)
                form.instance.repair = repair
                response = super().form_valid(form)
                repair.status = RepairRequest.Status.COMPLETED
                repair.save(update_fields=["status"])
        except IntegrityError:
            form.add_error(None, "A pickup is already recorded for this repair.")
            return self.form_invalid(form)
        messages.success(self.request, "Device pickup recorded; repair completed.")
        return response


class RelatedUpdateView(StaffRequiredMixin, UpdateView):
    template_name = "dashboard/record_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["cancel_url"] = reverse(
            "repair_detail", kwargs={"pk": self.get_object().repair_id}
        )
        return context

    def get_success_url(self):
        return reverse(
            "repair_detail", kwargs={"pk": self.object.repair_id}
        )


class DiagnosisUpdateView(RelatedUpdateView):
    model = Diagnosis
    form_class = DiagnosisForm
    title = "Edit diagnosis"


class RepairDetailUpdateView(RelatedUpdateView):
    model = RepairDetail
    form_class = RepairDetailForm
    title = "Edit repair work"


class PaymentUpdateView(RelatedUpdateView):
    model = Payment
    form_class = PaymentForm
    title = "Edit payment"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["repair"] = self.get_object().repair
        return kwargs

    def form_valid(self, form):
        repair_id = form.instance.repair_id
        with transaction.atomic():
            repair = RepairRequest.objects.select_for_update().get(pk=repair_id)
            paid_without_this_payment = repair.total_paid - form.instance.amount
            amount = form.cleaned_data["amount"]
            if (
                repair.final_cost is None
                or amount > repair.final_cost - paid_without_this_payment
            ):
                form.add_error(
                    "amount", "This amount exceeds the remaining repair balance."
                )
                return self.form_invalid(form)
            response = super().form_valid(form)
        messages.success(self.request, "Payment updated.")
        return response


class RepairPartUpdateView(RelatedUpdateView):
    model = RepairPart
    form_class = RepairPartForm
    title = "Edit part usage"

    def form_valid(self, form):
        try:
            with transaction.atomic():
                usage = RepairPart.objects.select_for_update().get(
                    pk=self.object.pk
                )
                old_part = Part.objects.select_for_update().get(pk=usage.part_id)
                new_part = Part.objects.select_for_update().get(
                    pk=form.cleaned_data["part"].pk
                )
                available = new_part.quantity_available
                if new_part.pk == old_part.pk:
                    available += usage.quantity
                if form.cleaned_data["quantity"] > available:
                    form.add_error("quantity", "Not enough inventory is available.")
                    return self.form_invalid(form)
                old_part.quantity_available += usage.quantity
                if new_part.pk == old_part.pk:
                    old_part.quantity_available -= form.cleaned_data["quantity"]
                    old_part.save(update_fields=["quantity_available"])
                else:
                    old_part.save(update_fields=["quantity_available"])
                    new_part.quantity_available -= form.cleaned_data["quantity"]
                    new_part.save(update_fields=["quantity_available"])
                    form.instance.unit_cost_at_use = new_part.unit_cost
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "The part usage could not be updated. Please retry.")
            return self.form_invalid(form)
        messages.success(self.request, "Part usage updated; inventory adjusted.")
        return response


class PickupUpdateView(RelatedUpdateView):
    model = Pickup
    form_class = PickupForm
    title = "Edit pickup record"


class SafeDeleteView(StaffRequiredMixin, DeleteView):
    template_name = "dashboard/confirm_delete.html"
    success_message = "Record deleted."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.get_success_url()
        return context

    def form_valid(self, form):
        success_url = self.get_success_url()
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "This record has related devices or repair history and cannot be deleted.",
            )
            return redirect(success_url)
        messages.success(self.request, self.success_message)
        return redirect(success_url)


class CustomerDeleteView(SafeDeleteView):
    model = Customer
    success_url = reverse_lazy("customer_list")


class DeviceDeleteView(SafeDeleteView):
    model = Device
    success_url = reverse_lazy("device_list")


class RepairDeleteView(SafeDeleteView):
    model = RepairRequest
    success_url = reverse_lazy("repair_list")

    def form_valid(self, form):
        if (
            self.object.diagnoses.exists()
            or self.object.work_entries.exists()
            or self.object.parts_used.exists()
            or self.object.payments.exists()
            or hasattr(self.object, "pickup")
        ):
            messages.error(
                self.request,
                "Repairs with history, parts, payments, or pickups cannot be deleted.",
            )
            return redirect(self.get_success_url())
        return super().form_valid(form)


class PartDeleteView(SafeDeleteView):
    model = Part
    success_url = reverse_lazy("part_list")


class RelatedDeleteView(SafeDeleteView):
    def get_success_url(self):
        return reverse(
            "repair_detail", kwargs={"pk": self.object.repair_id}
        )


class DiagnosisDeleteView(RelatedDeleteView):
    model = Diagnosis


class RepairDetailDeleteView(RelatedDeleteView):
    model = RepairDetail


class RepairPartDeleteView(RelatedDeleteView):
    model = RepairPart
    success_message = "Part usage removed and inventory restored."

    def form_valid(self, form):
        with transaction.atomic():
            usage = RepairPart.objects.select_for_update().get(pk=self.object.pk)
            part = Part.objects.select_for_update().get(pk=usage.part_id)
            part.quantity_available += usage.quantity
            part.save(update_fields=["quantity_available"])
            return super().form_valid(form)


class PaymentDeleteView(RelatedDeleteView):
    model = Payment


class PickupDeleteView(RelatedDeleteView):
    model = Pickup

    def form_valid(self, form):
        repair = self.object.repair
        repair.status = RepairRequest.Status.READY
        repair.save(update_fields=["status"])
        messages.success(self.request, "Pickup record removed; repair is ready again.")
        return super().form_valid(form)


class ReportView(ManagerRequiredMixin, TemplateView):
    template_name = "dashboard/report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repairs = RepairRequest.objects.all()
        filter_form = RepairFilterForm(self.request.GET or None)
        if filter_form.is_valid():
            status = filter_form.cleaned_data["status"]
            if status:
                repairs = repairs.filter(status=status)
            start = filter_form.cleaned_data["start_date"]
            end = filter_form.cleaned_data["end_date"]
            if start:
                repairs = repairs.filter(date_received__date__gte=start)
            if end:
                repairs = repairs.filter(date_received__date__lte=end)
        repair_ids = repairs.values("pk")
        context["repair_count"] = repairs.count()
        context["final_cost_total"] = (
            repairs.aggregate(total=Sum("final_cost"))["total"]
            or Decimal("0.00")
        )
        context["payment_total"] = (
            Payment.objects.filter(repair_id__in=repair_ids).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )
        context["status_totals"] = repairs.values("status").annotate(
            total=Count("pk")
        )
        context["repairs"] = repairs.select_related(
            "device__customer", "device"
        )[:100]
        context["filter_form"] = filter_form
        return context
