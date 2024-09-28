from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.shortcuts import HttpResponse, HttpResponseRedirect, render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User 
from django import forms
from django.db.models import Avg
from .models import Resource, Tag, Subject, Download, View, Profile, Rating, Comment
from django.contrib import messages
from django.db.models import F


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'avatar']

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirmation = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("confirmation")
        if password != confirmation:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = [
            'title',
            'description',
            'resource_type',
            'file_type',
            'file',
            'video_url',
            'subject',
            'tags',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'file': forms.FileInput(),
            'video_url': forms.URLInput(),
            'tags': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super(ResourceForm, self).__init__(*args, **kwargs)
        # Customize the fields as needed
        self.fields['tags'].queryset = Tag.objects.all()
        self.fields['subject'].queryset = Subject.objects.all()

        self.fields['tags'].required = False

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        video_url = cleaned_data.get('video_url')
        resource_type = cleaned_data.get('resource_type')

        # Ensure that either file or video_url is provided, but not both
        if not file and not video_url:
            raise forms.ValidationError('Either file or video URL must be provided.')
        if file and video_url:
            raise forms.ValidationError('Only one of file or video URL should be provided.')

        # Ensure resource_type matches the provided file or video_url
        if file and resource_type != 'Document':
            raise forms.ValidationError('Resource type must be "Document" when a file is provided.')
        if video_url and resource_type != 'Video':
            raise forms.ValidationError('Resource type must be "Video" when a video URL is provided.')

        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment_text']
        widgets = {
            'comment_text': forms.Textarea(attrs={'rows': 3}),
        }


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, str(i)) for i in range(1, 6)]),
        }



def index(request):

    # Authenticated users view their inbox
    if request.user.is_authenticated:
        return render(request, "library/index.html")

    # Everyone else is prompted to sign in
    else:
        return HttpResponseRedirect(reverse("login"))  

def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "library/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "library/login.html")
    
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "library/register.html", {"form": form})
    else:
        form = RegistrationForm()
    return render(request, "library/register.html", {"form": form})



@login_required
def upload_resource(request):
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.uploader = request.user
            resource.save()
            form.save_m2m()  # Save the many-to-many data for tags
            return redirect('resource_detail', resource_id=resource.id)
        else:
            # Form is invalid; render the form with errors
            return render(request, 'library/upload_resource.html', {'form': form})
    else:
        form = ResourceForm()
    return render(request, 'library/upload_resource.html', {'form': form})


@login_required
def profile_view(request, username=None):
    if username:
        # Viewing another user's profile
        user = get_object_or_404(User, username=username)
        is_own_profile = user == request.user
    else:
        # Viewing own profile
        user = request.user
        is_own_profile = True

    # Get uploaded resources
    uploaded_resources = Resource.objects.filter(uploader=user)

    # Get activity history (Downloads and Views)
    downloads = Download.objects.filter(user=user)
    views = View.objects.filter(user=user)

    context = {
        'profile_user': user,
        'is_own_profile': is_own_profile,
        'uploaded_resources': uploaded_resources,
        'downloads': downloads,
        'views': views,
    }
    return render(request, 'library/profile.html', context)


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was successfully updated!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'library/edit_profile.html', {'form': form})


def resource_detail(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id, is_active=True)
    
    # Record the view if the user is authenticated
    if request.user.is_authenticated:
        View.objects.get_or_create(user=request.user, resource=resource)
    
    # Update views count
    resource.views_count = F('views_count') + 1
    resource.save(update_fields=['views_count'])
    
    # Retrieve comments and ratings
    comments = Comment.objects.filter(resource=resource).select_related('user').order_by('-comment_date')
    average_rating = Rating.objects.filter(resource=resource).aggregate(Avg('rating'))['rating__avg'] or 0
    total_ratings = Rating.objects.filter(resource=resource).count()
    
    # Handle comment submission
    if request.method == 'POST' and 'comment_form' in request.POST:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.resource = resource
            comment.save()
            messages.success(request, 'Your comment has been posted.')
            return redirect('resource_detail', resource_id=resource.id)
    else:
        comment_form = CommentForm()
    
    # Handle rating submission
    if request.method == 'POST' and 'rating_form' in request.POST:
        rating_form = RatingForm(request.POST)
        if rating_form.is_valid():
            rating, created = Rating.objects.update_or_create(
                user=request.user,
                resource=resource,
                defaults={'rating': rating_form.cleaned_data['rating']}
            )
            messages.success(request, 'Your rating has been submitted.')
            return redirect('resource_detail', resource_id=resource.id)
    else:
        rating_form = RatingForm()
    
    # Check if the user has already rated
    user_rating = None
    if request.user.is_authenticated:
        try:
            user_rating = Rating.objects.get(user=request.user, resource=resource).rating
        except Rating.DoesNotExist:
            pass
    
    context = {
        'resource': resource,
        'comments': comments,
        'comment_form': comment_form,
        'rating_form': rating_form,
        'average_rating': round(average_rating, 1),
        'total_ratings': total_ratings,
        'user_rating': user_rating,
    }
    return render(request, 'library/resource_detail.html', context)
