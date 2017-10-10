from rest_framework import serializers
from rest_framework_mongoengine import serializers as mongoserializers

from app.models import Tool, Author, Book


class ToolSerializer(mongoserializers.DocumentSerializer):
    id = serializers.CharField(read_only=False)

    class Meta:
        model = Tool
        fields = '__all__'


class AuthorSerializer(mongoserializers.DocumentSerializer):
    class Meta:
        model = Author
        fields = '__all__'


class BookSerializer(mongoserializers.DocumentSerializer):
    class Meta:
        model = Book
        fields = '__all__'
