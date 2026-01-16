from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Letter, SectorProfile

@login_required
def sector_dashboard(request):

    # IDENTIFY THE USER
    try:
        user_profile = request.user.sectorprofile
        user_sector = user_profile.sector
    except SectorProfile.DoesNotExist:
        user_sector = "ADMIN"

    letters = Letter.objects.all().order_by('-date_received')

    selected_sector = request.GET.get('sector', 'ALL')

    if selected_sector != "ALL":
        letters = letters.filter(target_sector=selected_sector)

    # SEARCH LOGIC
    search_query = request.GET.get('q', '')

    if search_query:
        letters = letters.filter(
            Q(serial_number__icontains=search_query) |
            Q(sender_name__icontains=search_query) |
            Q(letter_type__icontains=search_query)
        )

    # CALCULATE STATS
    total_count = letters.count()
    resolved_count = letters.filter(is_replied=True).count()
    pending_count = total_count - resolved_count

    # HANDLE ACTIONS
    if request.method == 'POST':
        letter_id = request.POST.get('letter_id')
        reply_date = request.POST.get('reply_date')

        letter = get_object_or_404(Letter, id=letter_id, target_sector=user_sector)

        if not letter.is_replied and reply_date:
            letter.is_replied = True
            letter.replied_at = reply_date
            letter.save()

        return redirect(f"{request.path}?sector={selected_sector}")

    context = {
        'user_sector': user_sector,
        'selected_sector': selected_sector,
        'search_query': search_query,
        'letters': letters,
        'total': total_count,
        'pending': pending_count,
        'resolved': resolved_count,
    }

    return render(request, 'letters/dashboard.html', context)


@login_required
def letter_detail(request, pk):
    """
    New view to show full details of a single letter.
    """
    letter = get_object_or_404(Letter, pk=pk)

    try:
        user_profile = request.user.sectorprofile
        user_sector = user_profile.sector
    except SectorProfile.DoesNotExist:
        user_sector = "ADMIN"

    #SECURITY CHECK
    if user_sector != "ADMIN" and letter.target_sector != user_sector:
        return render(request, 'letters/access_denied.html', {})

    return render(request, 'letters/letter_detail.html', {
        'letter': letter,
        'user_sector': user_sector
    })