from django.contrib import admin

from .models import (
    Profile,
    Subject,
    Tag,
    Resource,
    ResourceTag,
    Rating,
    Comment,
    Bookmark,
    Download,
    View,
)

admin.site.register(Profile)
admin.site.register(Subject)
admin.site.register(Tag)
admin.site.register(Resource)
admin.site.register(ResourceTag)
admin.site.register(Rating)
admin.site.register(Comment)
admin.site.register(Bookmark)
admin.site.register(Download)
admin.site.register(View)
