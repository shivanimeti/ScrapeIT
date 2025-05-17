from django.db import models

class SearchResult(models.Model):
    keyword = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    url = models.URLField()
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.keyword} - {self.url}"

class ContactInfo(models.Model):
    url = models.URLField()
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.url
