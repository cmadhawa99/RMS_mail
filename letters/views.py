from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Letter, SectorProfile
from django.views.decorators.cache import never_cache  # <--- CRITICAL SECURITY TOOL
from django.core.paginator import Paginator
from .forms import UserForm, LetterForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import logout  # <--- Needed for logout


# --- PUBLIC PORTAL ---

@never_cache  # Security: Prevents "Back" button from showing this after logout
@login_required
def sector_dashboard(request):
    if request.user.is_superuser:
        return redirect('custom_admin_dashboard')

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


# ------- CUSTOM ADMIN PANEL VIEWS -------

@never_cache
@login_required
def custom_admin_dashboard(request):
    if not request.user.is_superuser: return redirect('sector_dashboard')
    return render(request, 'letters/admin_dashboard.html')


@never_cache
@login_required
def custom_admin_users(request):
    if not request.user.is_superuser: return redirect('sector_dashboard')
    users = User.objects.filter(is_superuser=False).select_related('sectorprofile')

    search_query = request.GET.get('q', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    return render(request, 'letters/admin_users.html', {'users': users, 'search_query': search_query})


@never_cache
@login_required
def custom_admin_letters(request):
    if not request.user.is_superuser: return redirect('sector_dashboard')
    letters_list = Letter.objects.all().order_by('-date_received')

    search_query = request.GET.get('q', '')
    if search_query:
        letters_list = letters_list.filter(
            Q(serial_number__icontains=search_query) |
            Q(sender_name__icontains=search_query) |
            Q(letter_type__icontains=search_query) |
            Q(target_sector__icontains=search_query)
        )

    paginator = Paginator(letters_list, 20)
    page_number = request.GET.get('page')
    letters = paginator.get_page(page_number)
    return render(request, 'letters/admin_letters.html', {'letters': letters, 'search_query': search_query})


# --- ADMIN DETAILS (With Security) ---

@never_cache
@login_required
def admin_user_detail(request, user_id):
    if not request.user.is_superuser: return redirect('sector_dashboard')
    user_obj = get_object_or_404(User, pk=user_id)
    return render(request, 'letters/admin_user_detail.html', {'user_obj': user_obj})


@never_cache
@login_required
def admin_letter_detail(request, pk):
    if not request.user.is_superuser: return redirect('sector_dashboard')
    letter = get_object_or_404(Letter, pk=pk)
    return render(request, 'letters/admin_letter_detail.html', {'letter': letter})


# --- ACTION VIEWS ---

@never_cache
@login_required
def create_user(request):
    if not request.user.is_superuser: return redirect('sector_dashboard')

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New officer account created successfully!")
            return redirect('custom_admin_users')
    else:
        form = UserForm()

    return render(request, 'letters/user_form.html', {'form': form, 'title': 'Create New Officer'})


@never_cache
@login_required
def edit_user(request, user_id):
    if not request.user.is_superuser: return redirect('sector_dashboard')

    user_obj = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Details for {user_obj.username} updated.")
            return redirect('admin_user_detail', user_id=user_obj.id)
    else:
        form = UserForm(instance=user_obj)

    return render(request, 'letters/user_form.html', {'form': form, 'title': 'Edit Officer Details'})


@login_required
def delete_user(request, user_id):
    if not request.user.is_superuser: return redirect('sector_dashboard')

    if request.method == 'POST':
        user_to_delete = get_object_or_404(User, pk=user_id)
        if not user_to_delete.is_superuser:
            user_to_delete.delete()
            messages.success(request, "User account deleted.")

    return redirect('custom_admin_users')


@never_cache
@login_required
def add_letter(request):
    if not request.user.is_superuser: return redirect('sector_dashboard')

    if request.method == 'POST':
        form = LetterForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "New letter added successfully.")
            return redirect('custom_admin_letters')
    else:
        form = LetterForm()

    return render(request, 'letters/letter_form.html', {'form': form, 'title': 'Add New Letter'})


@never_cache
@login_required
def edit_letter(request, pk):
    if not request.user.is_superuser: return redirect('sector_dashboard')
    letter = get_object_or_404(Letter, pk=pk)

    if request.method == 'POST':
        form = LetterForm(request.POST, request.FILES, instance=letter)
        if form.is_valid():
            form.save()
            messages.success(request, "Letter updated successfully.")
            return redirect('admin_letter_detail', pk=letter.pk)
    else:
        form = LetterForm(instance=letter)

    return render(request, 'letters/letter_form.html', {'form': form, 'title': 'Edit Letter'})


@login_required
def delete_letter(request, pk):
    if not request.user.is_superuser: return redirect('sector_dashboard')

    letter = get_object_or_404(Letter, pk=pk)
    if request.method == 'POST':
        letter.delete()
        messages.success(request, "Letter permanently deleted.")

    return redirect('custom_admin_letters')


# --- LOGOUT VIEW (NEW) ---

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')