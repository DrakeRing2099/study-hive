from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

# Profile model to extend User model with additional fields
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return self.user.username

# Signal to create or update Profile when User is saved
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

# Subject model for categorizing resources
class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

# Tag model for resource tagging
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

# Resource model for study materials
class Resource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('Document', 'Document'),
        ('Video', 'Video'),
    ]
    FILE_TYPE_CHOICES = [
        ('PDF', 'PDF'),
        ('PPT', 'PPT'),
        ('DOC', 'DOC'),
        ('DOCX', 'DOCX'),
        ('YouTube', 'YouTube'),
        # Add other file types as needed
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file = models.FileField(upload_to='resources/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_resources')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='resources')
    views_count = models.IntegerField(default=0)
    downloads_count = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    total_ratings = models.IntegerField(default=0)
    bookmarks = models.ManyToManyField(User, through='Bookmark', related_name='bookmarked_resources')
    is_active = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, through='ResourceTag', related_name='resources')

    def __str__(self):
        return self.title

    def clean(self):
        # Ensure that either file or video_url is provided, but not both
        if not self.file and not self.video_url:
            raise ValidationError('Either file or video URL must be provided.')
        if self.file and self.video_url:
            raise ValidationError('Only one of file or video URL should be provided.')
        # Ensure resource_type matches the provided file or video_url
        if self.file and self.resource_type != 'Document':
            raise ValidationError('Resource type must be "Document" when a file is provided.')
        if self.video_url and self.resource_type != 'Video':
            raise ValidationError('Resource type must be "Video" when a video URL is provided.')

    class Meta:
        pass

# Through model for Resource-Tag many-to-many relationship
class ResourceTag(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='resource_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='resource_tags')

    class Meta:
        unique_together = ('resource', 'tag')

    def __str__(self):
        return f'{self.resource.title} - {self.tag.name}'

# Rating model for user ratings on resources
class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    rating_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'resource')

    def __str__(self):
        return f'{self.user.username} rated {self.resource.title} - {self.rating}'

# Comment model for feedback on resources
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='comments')
    comment_text = models.TextField()
    comment_date = models.DateTimeField(auto_now_add=True)
    parent_comment = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')

    def __str__(self):
        return f'Comment by {self.user.username} on {self.resource.title}'

# Bookmark model for saving resources
class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='bookmarked_by')
    bookmark_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'resource')

    def __str__(self):
        return f'{self.user.username} bookmarked {self.resource.title}'

# Download model to track resource downloads
class Download(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='downloads')
    download_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} downloaded {self.resource.title}'

# View model to track resource views
class View(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='views')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='views')
    view_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} viewed {self.resource.title}'

