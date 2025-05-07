from django.contrib import admin
from django.utils.html import format_html
from .models import Stock, BloodRequest

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('bloodgroup', 'unit', 'cost_per_unit', 'last_updated')
    list_editable = ('unit', 'cost_per_unit')
    list_filter = ('bloodgroup',)
    search_fields = ('bloodgroup',)
    ordering = ('bloodgroup',)
    readonly_fields = ('last_updated',)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields
        return ()

@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'bloodgroup', 'unit', 'display_cost_at_request', 'display_total_cost', 'status', 'request_date')
    list_filter = ('status', 'bloodgroup')
    search_fields = ('patient_name', 'bloodgroup')
    ordering = ('-request_date',)
    readonly_fields = ('cost_at_request', 'total_cost', 'display_cost_at_request', 'display_total_cost')

    def display_cost_at_request(self, obj):
        if obj.cost_at_request is not None:
            return format_html('${:.2f}', obj.cost_at_request)
        return '-'
    display_cost_at_request.short_description = 'Cost per Unit'
    display_cost_at_request.admin_order_field = 'cost_at_request'

    def display_total_cost(self, obj):
        if obj.total_cost is not None:
            return format_html('${:.2f}', obj.total_cost)
        return '-'
    display_total_cost.short_description = 'Total Cost'
    display_total_cost.admin_order_field = 'total_cost'

    def get_fields(self, request, obj=None):
        fields = ['patient_name', 'patient_age', 'reason', 'bloodgroup', 'unit', 'status']
        if obj:  # if editing an existing object
            fields.extend(['display_cost_at_request', 'display_total_cost'])
        return fields
