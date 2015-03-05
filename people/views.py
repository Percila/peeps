from django.shortcuts import render
from django.contrib import messages

import ijson
import os
from whoosh.fields import Schema, TEXT
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser


main_schema = Schema(name=TEXT(stored=True),
                     address=TEXT(stored=True),
                     friends=TEXT(stored=True),
                     company=TEXT(stored=True))

may_know_schema = Schema(knower=TEXT(stored=True),
                         knowee=TEXT(stored=True),
                         friends=TEXT(stored=True),
                         reason=TEXT(stored=True))

we_dont_have_schema = Schema(name=TEXT(stored=True))

if not os.path.exists("main_index"):
    os.mkdir("main_index")
main_ix = create_in("main_index", main_schema)
main_ix = open_dir("main_index")

if not os.path.exists("may_know_index"):
    os.mkdir("may_know_index")
may_know_ix = create_in("may_know_index", may_know_schema)
may_know_ix = open_dir("may_know_index")

if not os.path.exists("dont_have_index"):
    os.mkdir("dont_have_index")
we_dont_have_ix = create_in("dont_have_index", we_dont_have_schema)
we_dont_have_ix = open_dir("dont_have_index")


current_dir = os.path.dirname(__file__)
json_path = os.path.join(current_dir, 'static/people.json')


def home(request):
    return render(request, 'home.html')


def profile(request):
    user = request.GET['firstname'].strip() + " " + request.GET['lastname'].strip()

    with main_ix.searcher() as searcher:
        query_person = QueryParser("name", main_ix.schema).parse(unicode(user))
        person_results = searcher.search(query_person)

        with may_know_ix.searcher() as searcher:
            query_may_know = QueryParser("knower", may_know_ix.schema).parse(unicode(user))
            may_know_results = searcher.search(query_may_know)

            if len(person_results) is not 0:

                for result in person_results:
                    person = {}
                    details = result.fields()
                    person['name'] = details['name']
                    friends = []
                    friends_list = details['friends'].split(",")

                    for friend in friends_list:
                        friends.append(dict(zip(['name'], [friend])))
                    person['friends'] = friends

                    if len(may_know_results) is not 0:
                        maybe_list = []

                        for may_know in may_know_results:
                            maybe = {}
                            details = may_know.fields()
                            maybe['name'] = details['knowee']
                            maybe['reason'] = details['reason']
                            maybe_list.append(maybe)

                        return render(request, 'profile.html', {'person': person, 'may_know_list': [maybe_list]})

                    return render(request, 'profile.html', {'person': person})

            else:

                person = get_persons('name', user)
                may_know_list = []

                for p in person:
                    city = p['address'].split(", ")[1]
                    city_dwellers_generator = get_persons('address', city)

                    for city_dweller in city_dwellers_generator:
                        may_know_list.append([{'name': city_dweller['name'], 'reason': "They also live in {}".format(city)}])

                    for friend in p['friends']:
                        may_know_list.append(get_may_know_list(friend['name']))
                        may_know_list = filter(lambda complete_list: complete_list is not None, may_know_list)

                    may_know_writer = may_know_ix.writer()

                    for may_know in may_know_list:

                        for each_may_know in may_know:
                            may_know_writer.add_document(knower=p['name'], knowee=each_may_know['name'], reason=unicode(each_may_know['reason']))
                    may_know_writer.commit()

                    current_friends = []
                    writer = main_ix.writer()

                    for friend in p['friends']:
                        current_friends.append(friend['name'])
                    writer.add_document(name=p['name'], address=p['address'], company=p['company'], friends=",".join(current_friends))
                    writer.commit()

                    return render(request, 'profile.html', {'person': p, 'may_know_list': may_know_list})

                messages.error(request, "Sorry you are not yet in our system")

                return render(request, 'home.html')


def search(request):
    search_term = request.GET['search'].strip()

    with we_dont_have_ix.searcher() as searcher:
        peeps_we_dont_have_query = QueryParser("name", we_dont_have_ix.schema).parse(unicode(search_term))
        peeps_we_dont_have_results = searcher.search(peeps_we_dont_have_query)

        if len(peeps_we_dont_have_results) is not 0:
            return render(request, 'search_results.html', {'error': 'Person with name {} not found'.format(search_term)})

    with main_ix.searcher() as searcher:
        query = QueryParser("name", main_ix.schema).parse(unicode(search_term))
        results = searcher.search(query)

        if len(results) is not 0:
            for result in results:
                return render(request, 'search_results.html', {'results': result.fields()})

        else:

            person = get_persons('name', search_term)
            results = []

            for p in person:
                current_friends = []

                for friend in p['friends']:
                        current_friends.append(friend['name'])
                writer = main_ix.writer()
                writer.add_document(name=p['name'], address=p['address'], company=p['company'], friends=','.join(current_friends))
                writer.commit()
                results.append({'name': p['name'], 'address': p['address'], 'company': p['company'], 'friends': current_friends})

                return render(request, 'search_results.html', {'results': results.fields()})

            we_dont_have_writer = we_dont_have_ix.writer()
            we_dont_have_writer.add_document(name=search_term)
            we_dont_have_writer.commit()

            return render(request, 'search_results.html', {'error': 'Person with name {} not found'.format(search_term)})


def get_persons(field, name):
    all_people = get_all_fields('result.item')
    return (p for p in all_people if name.lower() in p[field].lower())


def get_all_fields(prefix):
    json_file = open(json_path)
    return ijson.items(json_file, prefix)


def get_may_know_list(name):
    person = get_persons('name', name)

    for p in person:
        may_know_list = []

        for friend in p['friends']:
            may_know_list.append({'name': friend['name'], 'reason': "You are both friends with " + name})

        return may_know_list
