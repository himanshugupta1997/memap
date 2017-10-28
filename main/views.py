from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt


from clarifai.rest import ClarifaiApp
from taggit.models import Tag
from PIL import Image

from .models import Item, Note



def detect(filename):   
    app = ClarifaiApp(api_key='ddca6c15086d4d57835c5cc782df6505')
    model = app.models.get("general-v1.3")
    data = model.predict_by_filename(filename)
    new = [x['name'] for x in data['outputs'][0]['data']['concepts'] if x['value']>=0.95]
    xfilter = lambda old,new: len(set(new).intersection(set(old))) / len(new)

    old = [[tag.name for tag in item.tags.all()] for item in Item.objects.all()]
    matches = sorted([(idx,xfilter(x,new)) for idx,x in enumerate(old) if xfilter(x,new)>=0.0], key=lambda x:x[1])

    if not matches:
        return None

    final = []

    for idx,x in enumerate(Item.objects.all()):
        if idx in list(zip(*matches))[0]:
            final.append(x)

    return final[0]


@login_required
def index(request):
    if not request.user.is_authenticated():    
        print("GO")
    else:

        if request.method == "GET":
            return render(request, 'index.html')

        else:
            filename = "test.jpg"
            Image.open(request.FILES['img']).save(filename)
            item = detect(filename)
            return render(request, 'results.html', {'item':item})
    return HttpResponse("Yo")


@login_required
def view_notes(request, item_id):
    if not request.user.is_authenticated():    
        print("GO")
    else:

        if request.method == "GET":
            notes = Note.objects.filter(item__id = item_id)
            return render(request, 'notes.html', {'notes':notes})

















"""
def link(request, id):
    link = get_object_or_404(Link, id = id)
    link_time = humanize.naturaltime(datetime.now(timezone.utc) - link.date)
    comment_form = CommentForm()
    upvotes = link.votes.count(action = UP)
    downvotes = link.votes.count(action = DOWN)
    if request.user.is_authenticated():
        upvoted = link.votes.exists(request.user.id, action = UP)
        downvoted = link.votes.exists(request.user.id, action = DOWN)
        # upvote button config
        if not upvoted:
            upvote_button = ""
        else:
            upvote_button = vote_color

        # downvote button config
        if not downvoted:
            downvote_button = ""
        else:
            downvote_button = vote_color
    else:
        upvote_button = ""
        downvote_button = ""

    return render(request, 'links/link.html', 
        {'link': link, 'comment_form': comment_form, 'upvotes': upvotes, 
        'downvotes': downvotes, 'time': link_time,
        'upvote_button': upvote_button, 'downvote_button': downvote_button})


def book(request, id):
    book = get_object_or_404(Book, id=id)
    links = book.link_set.all()
    return render(request, 'links/book.html', {'links': links, 'book':book})


@login_required
def create_link(request):
    if request.method == 'POST':
        link = Link()
        link.user = request.user
        link.url = request.POST.get('URL')
        link.title = striphtml(request.POST.get('TITLE'))
        link.description = striphtml(request.POST.get('DESCRIPTION'))
        link.save()
        tag_list = request.POST.get('TAGS')
        for tag in _parse_tags(tag_list):
            link.tags.add(striphtml(tag))
        for book_name in request.POST.getlist('BOOKS'):
            link.books.add(Book.objects.get(user = request.user, title = book_name))
        link.save()
        return redirect('/link/{}/'.format(link.id))
    else:
        books = Book.objects.filter(user = request.user)
        return render(request, 'links/new_link.html', {'books': books})


@login_required
def edit_link(request, id):
    link = get_object_or_404(Link, id = id)
    books = Book.objects.filter(user = request.user)
    if request.method == 'POST':
        link.url = request.POST.get('URL')
        link.title = striphtml(request.POST.get('TITLE'))
        link.description = striphtml(request.POST.get('DESCRIPTION'))
        for tag in link.tags.all():
            link.tags.remove(tag)
        tag_list = request.POST.get('TAGS')
        for tag in _parse_tags(tag_list):
            link.tags.add(striphtml(tag))

        new_book_list = request.POST.getlist('BOOKS')
        for book in books:
            if book in link.books.all() and book.title not in new_book_list:
                link.books.remove(book)
            elif book not in link.books.all() and book.title in new_book_list:
                link.books.add(book)
        link.save_og()
        link.save()
        return redirect('/link/{}/'.format(link.id))
    else:
        tag_text = ", ".join(tag.name for tag in link.tags.all())
        return render(request, 'links/edit_link.html', {'link':link, 'books': books, 'tag_text': tag_text})


@login_required
def import_link(request, id):
    if request.method == 'POST':
        book = Book.objects.get(id = id)
        new_links = [Link.objects.get(id = int(id)) for id in request.POST.getlist('LINKS')]
        for link in new_links:
            link.books.add(book)
            link.save()
        book.save()
        return redirect('/{}/?show=links'.format(book.user.username))


@login_required
def delete_link(request, id):
    if request.is_ajax():
        Link.objects.get(id = id).delete()
        return JsonResponse({'status':1})


@login_required
def vote_link(request, id):
    if request.method == 'GET':
        vote_type = request.GET['type']
        link = Link.objects.get(id = id)
        upvoted = link.votes.exists(request.user.id, action = UP)
        downvoted = link.votes.exists(request.user.id, action = DOWN)

        if vote_type == "U":
            if not upvoted:
                link.votes.up(request.user.id)
                link.save()
                request.user.profile.upvoted_links.add(link)
                upvote_button = vote_color
                downvote_button = ""
                if link.user != request.user:
                    notify.send(request.user, recipient = link.user, 
                        target = link, verb = "upvoted")
            else:
                link.votes.delete(request.user.id)
                link.save()
                request.user.profile.upvoted_links.remove(link)
                upvote_button = ""
                downvote_button = ""

            link.num_vote_down = link.votes.count(action = DOWN)
            link.num_vote_up = link.votes.count(action = UP)
            link.save()
        
            return JsonResponse({'upvotes': link.votes.count(action = UP), 
                'downvotes': link.votes.count(action = DOWN),
                'upvote_button': upvote_button,
                'downvote_button': downvote_button})


        elif vote_type == "D":
            if not downvoted:
                link.votes.down(request.user.id)
                link.save()
                if link in request.user.profile.upvoted_links.all():
                    request.user.profile.upvoted_links.remove(link)
                downvote_button = vote_color
                upvote_button = ""
                if link.user != request.user:
                    notify.send(request.user, recipient = link.user, 
                        target = link, verb = "downvoted")
            else:
                link.votes.delete(request.user.id)
                link.save()
                downvote_button = ""
                upvote_button = ""

            link.num_vote_down = link.votes.count(action = DOWN)
            link.num_vote_up = link.votes.count(action = UP)
            link.save()
            
            return JsonResponse({'upvotes': link.votes.count(action = UP),
                'downvotes': link.votes.count(action = DOWN),
                'upvote_button': upvote_button,
                'downvote_button': downvote_button})

        
@login_required
def create_book(request):
    if request.method == 'POST':
        books = Book.objects.filter(user = request.user).filter(title = request.POST.get('TITLE'))
        
        # book with same name
        if len(books):
            error = "Book with this name already exists!"
            return render(request, 'links/new_book.html', {'error':error})

        book = Book()
        book.user = request.user
        book.title = striphtml(request.POST.get('TITLE'))
        book.description = striphtml(request.POST.get('DESCRIPTION'))
        book.save()
        
        return redirect('/'+request.user.username+'/?show=links')
    else:
        return render(request, 'links/new_book.html')


@login_required
def edit_book(request, id):
    book = get_object_or_404(Book, id = id)
    if request.method == 'POST':
        book.title = striphtml(request.POST.get('TITLE'))
        book.description = striphtml(request.POST.get('DESCRIPTION'))
        book.save()
        return redirect("/book/{}/".format(id))
    else:
        return render(request, 'links/edit_book.html', {'book':book})


@login_required
def remove_book_link(request, b_id, l_id):
    if request.is_ajax():
        link = Link.objects.get(id = l_id)
        link.books.remove(Book.objects.get(id = b_id))
        link.save()
        return JsonResponse({'status':1})



@login_required
def delete_book(request, id):
    if request.is_ajax():
        Book.objects.get(id = id).delete()
        return JsonResponse({'status':1})


def ajax_load_comment(request):
    if request.is_ajax():
        comments = []
        for comment in Comment.objects.filter(link__id = request.GET.get('link_id')):
            c = {}
            c['id'] = comment.id
            c['text'] = comment.text
            c['user'] = comment.user.username
            c['pic'] = comment.user.profile.pic
            c['time'] = humanize.naturaltime(datetime.now(timezone.utc) - comment.date)
            comments.append(c)
        return JsonResponse({'comments':comments, 'count': len(comments)})


@csrf_exempt
@login_required
def ajax_create_comment(request):
    if request.is_ajax():
        comment = Comment()
        comment.user = request.user
        comment.link = Link.objects.get(id = request.POST.get('link_id'))
        comment.text = striphtml(request.POST.get('text'))
        comment.save()
        if comment.user != request.user:
            notify.send(request.user, recipient = comment.link.user, 
                target = comment.link, verb = "commented on")
        return JsonResponse({'done': True})



@csrf_exempt
@login_required
def ajax_edit_comment(request, id):
    if request.is_ajax():
        comment = Comment.objects.get(id = id)
        comment.text = striphtml(request.POST.get('text'))
        comment.save()
        return JsonResponse({'done': True})


@login_required
def ajax_delete_comment(request, id):
    if request.is_ajax():
        Comment.objects.get(id = id).delete()
        return JsonResponse({'done': True})


def view_tag(request, id, tag_name):
    tagged = Link.objects.filter(tags__name = tag_name)
    return render(request, "links/tags.html/", {'tag': tagged, 'tagname' : tag_name})


'''
# not required now
@login_required
def create_comment(request, id):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = Comment()
            comment.user = request.user
            comment.link = Link.objects.get(id = id)
            comment.text = form.cleaned_data.get('text')
            comment.save()
            notify.send(request.user, recipient = comment.link.user, 
                target = comment.link, verb = "commented on")
            return redirect('/link/{}'.format(id))
'''
"""