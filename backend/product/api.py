from typing import List, Literal, Optional

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import PageNumberPagination, paginate

from .models import Product
from .schemas import ProductSchema

router = Router()


@router.get("/", response=List[ProductSchema])
@paginate(PageNumberPagination, page_size=20)
def list_products(
    request,
    category: Optional[str] = None,
    type_filter: Optional[str] = None,
    price_type: Optional[Literal["fixed", "quote"]] = None,
    q: Optional[str] = None,
):
    qs = Product.objects.prefetch_related("images").all()
    if category:
        qs = qs.filter(category__iexact=category)
    if type:
        qs = qs.filter(type__iexact=type_filter)
    if price_type:
        qs = qs.filter(price_type=price_type)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return qs


@router.get("/{product_id}", response=ProductSchema)
def get_product(request, product_id: int):
    return get_object_or_404(Product, id=product_id)
