from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Letter, SectorProfile
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator

@never_cache
@login_required
def sector_dashboard(request):
    try:
        user_profile = request.user.sectorprofile
        user_sector = user_profile.sector
    except SectorProfile.DoesNotExist:
        if request.user.is_superuser:
            user_sector = "ADMIN"
        else:
            user_sector = "NONE"

    letters = Letter.objects.all().order_by('-date_received')

    selected_sector = request.GET.get('sector', 'ALL')

    if selected_sector != "ALL":
        letters = letters.filter(target_sector=selected_sector)

    search_query = request.GET.get('q', '')

    if search_query:
        letters = letters.filter(
            Q(serial_number__icontains=search_query) |
            Q(sender_name__icontains=search_query) |
            Q(letter_type__icontains=search_query)
        )

    total_count = letters.count()
    resolved_count = letters.filter(is_replied=True).count()
    pending_count = total_count - resolved_count

    paginator = Paginator(letters, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        letter_id = request.POST.get('letter_id')
        reply_date = request.POST.get('reply_date')

        letter = get_object_or_404(Letter, pk=letter_id, target_sector=user_sector)

        if not letter.is_replied and reply_date:
            letter.is_replied = True
            letter.replied_at = reply_date
            letter.save()

        return redirect(f"{request.path}?sector={selected_sector}&page={page_obj.number}")

    context = {
        'user_sector': user_sector,
        'selected_sector': selected_sector,
        'search_query': search_query,
        'letters': page_obj,
        'total': total_count,
        'pending': pending_count,
        'resolved': resolved_count,
    }

    return render(request, 'letters/dashboard.html', context)

@never_cache
@login_required
def letter_detail(request, pk):
    letter = get_object_or_404(Letter, pk=pk)

    try:
        user_profile = request.user.sectorprofile
        user_sector = user_profile.sector
    except SectorProfile.DoesNotExist:
        if request.user.is_superuser:
            user_sector = "ADMIN"
        else:
            user_sector = "NONE"

    if user_sector != "ADMIN" and letter.target_sector != user_sector:
        return render(request, 'letters/access_denied.html')

    return render(request, 'letters/letter_detail.html', {
        'letter': letter,
        'user_sector': user_sector
    })

