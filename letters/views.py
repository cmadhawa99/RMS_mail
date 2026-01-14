from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Letter, SectorProfile

@login_required
def sector_dashboard(request):
    try:
        user_profile = request.user.sectorprofile
        user_sector = user_profile.sector
    except SectorProfile.DoesNotExist:
        user_sector = "ADMIN"

    selected_sector = request.GET.get('sector', 'ALL')

    if selected_sector == "ALL":
        letters = Letter.objects.all().order_by('-date_received')
    else:
        letters = Letter.objects.filter(target_sector=selected_sector).order_by('-date_received')

    all_letters = Letter.objects.all()
    total_count = all_letters.count()
    resolved_count = all_letters.filter(is_repaired=True).count()
    pending_count = total_count - resolved_count

    if request.method == 'POST':
        letter_id = request.POST.get('letter_id')
        letter = get_object_or_404(Letter, id=letter_id, target_sector=user_sector)
        if not letter.is_replied:
            letter.is_replied = True
            letter.save()
        return redirect('dashboard')

    context = {
        'user_sector': user_sector,
        'selected_sector': selected_sector,
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

    return render(request, 'letters/letter_detail.html', {
        'letter': letter,
        'user_sector': user_sector
    })