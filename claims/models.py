from django.db import models
from django.contrib.auth.models import User

# Core claim data, loaded from CSV/JSON
class Claim(models.Model):
    id = models.IntegerField(primary_key=True)
    patient_name = models.CharField(max_length=255)
    billed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status_choices = [
        ('Paid', 'Paid'),
        ('Denied', 'Denied'),
        ('Under Review', 'Under Review'),
    ]
    status = models.CharField(max_length=50, choices=status_choices)
    insurer_name = models.CharField(max_length=255)
    discharge_date = models.DateField()
    burger_combo_code = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['patient_name']),  # For search functionality
            models.Index(fields=['insurer_name']),  # For search functionality
            models.Index(fields=['status']),  # For status filtering
            models.Index(fields=['discharge_date']),  # For date-based queries
            models.Index(fields=['-id']),  # For pagination (already primary key, but explicit for ordering)
        ]

    def __str__(self):
        return f"Claim {self.id} for {self.patient_name}"

# Detailed claim information
class ClaimDetail(models.Model):
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name='details')
    cpt_codes = models.CharField(max_length=255)  # e.g., "99204, 82947, 99406"
    denial_reason = models.TextField(max_length=2000, blank=True, null=True)  # Add reasonable length limit

    def __str__(self):
        return f"Details for Claim {self.claim.id}"

# User-generated flag
class Flag(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='flags')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, default="Flagged for review")

    class Meta:
        # A user can only flag a specific claim once
        unique_together = ('claim', 'user')
        indexes = [
            models.Index(fields=['claim', '-created_at']),  # For efficient flag retrieval
            models.Index(fields=['-created_at']),  # For recent flags queries
        ]

# User-generated note
class Note(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=5000)  # Add reasonable length limit
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['claim', '-created_at']),  # For efficient note retrieval
            models.Index(fields=['-created_at']),  # For recent notes queries
        ]

    def __str__(self):
        return f"Note by {self.user.username} on Claim {self.claim.id}"
