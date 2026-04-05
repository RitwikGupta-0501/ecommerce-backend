from django.db import models
from django.utils.text import slugify


class Product(models.Model):
    class PriceTypes(models.TextChoices):
        FIXED = "fixed", "Fixed"
        QUOTE = "quote", "Quote"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=False, unique=True)
    description = models.TextField()

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_type = models.CharField(
        max_length=10, choices=PriceTypes.choices, default=PriceTypes.FIXED
    )

    # Categories & Metadata
    category = models.CharField(
        max_length=100, help_text="Category like Software, Hardware"
    )
    type = models.CharField(
        max_length=300,
        help_text="License Type like Perpetual Licnese, Annual License, etc.",
    )
    # TODO: Update to actual reviews and ratings system
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    reviews = models.IntegerField(default=0)

    # Text-based lists are fine in JSONField (Admin can type these as JSON/Text)
    features = models.JSONField(default=list, blank=True)
    specifications = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="products/gallery/")
    alt_text = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.product.name}"
