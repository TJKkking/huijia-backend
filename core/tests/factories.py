import factory
from core.models import User, Post, Comment, Category, Tag

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    nickname = factory.Sequence(lambda n: f'User {n}')
    is_phone_verified = True
    phone = factory.Sequence(lambda n: f'1380000{n:04d}')

class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.Sequence(lambda n: f'category-{n}')
    description = factory.Faker('text', max_nb_chars=200)

class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f'Tag {n}')
    slug = factory.Sequence(lambda n: f'tag-{n}')

class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    title = factory.Sequence(lambda n: f'Post {n}')
    content = factory.Faker('text')
    author = factory.SubFactory(UserFactory)
    status = 'published'
    is_anonymous = False
    is_pinned = False

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)
        else:
            # 默认添加两个标签
            self.tags.add(TagFactory())
            self.tags.add(TagFactory())

class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    content = factory.Faker('text')
    author = factory.SubFactory(UserFactory)
    post = factory.SubFactory(PostFactory)
    is_anonymous = False 