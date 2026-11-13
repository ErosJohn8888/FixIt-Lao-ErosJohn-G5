from django.contrib import admin

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


class ReadOnlyModelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Customer)
class CustomerAdmin(ReadOnlyModelAdmin):
    list_display = ("full_name", "phone", "email", "created_at")
    search_fields = ("full_name", "phone", "email")


@admin.register(Device)
class DeviceAdmin(ReadOnlyModelAdmin):
    list_display = ("brand", "model", "device_type", "customer", "serial_number")
    search_fields = ("brand", "model", "serial_number", "customer__full_name")


@admin.register(RepairRequest)
class RepairRequestAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "device", "status", "date_received", "received_by")
    list_filter = ("status", "date_received")
    search_fields = ("device__customer__full_name", "device__serial_number")


admin.site.register(
    [Diagnosis, RepairDetail, Part, RepairPart, Payment, Pickup],
    ReadOnlyModelAdmin,
)
