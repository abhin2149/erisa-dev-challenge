from django.contrib import admin
from .models import Claim, ClaimDetail, Flag, Note


# Register your models here.
@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_name', 'billed_amount', 'paid_amount', 'status', 'insurer_name', 'discharge_date')
    list_filter = ('status', 'insurer_name', 'discharge_date')
    search_fields = ('id', 'patient_name', 'insurer_name')
    readonly_fields = ('id',)
    ordering = ('-id',)
    list_per_page = 50


@admin.register(ClaimDetail)
class ClaimDetailAdmin(admin.ModelAdmin):
    list_display = ('claim', 'cpt_codes', 'denial_reason')
    search_fields = ('claim__id', 'claim__patient_name', 'cpt_codes')
    list_filter = ('claim__status',)


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ('claim', 'user', 'reason', 'created_at')
    list_filter = ('created_at', 'user')
    ordering = ('-created_at',)
    search_fields = ('claim__id', 'claim__patient_name', 'user__username')


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('claim', 'user', 'text_preview', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('claim__id', 'claim__patient_name', 'user__username', 'text')
    ordering = ('-created_at',)
    
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = "Note Preview"