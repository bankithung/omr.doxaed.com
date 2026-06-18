from django.contrib import admin

from folders.models import Folder, FolderShare

admin.site.register(Folder)
admin.site.register(FolderShare)
