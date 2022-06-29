from django.db import models


class Candidate(models.Model):
    name = models.TextField(blank=False)
    address = models.TextField(blank=True, null=True)
    contact_details = models.JSONField(blank=True, null=True)
    location = models.TextField(blank=False)
    tech_skills = models.JSONField()

    def __str__(self):
        return self.name

