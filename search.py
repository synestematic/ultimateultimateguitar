import sys
import html
import base64

from urllib.parse import quote
from datetime import datetime

from bestia.iterate import LoopedList
from bestia.output import FString, echo, Row, tty_cols

import ultimateultimateguitar

MAIN_URL = base64.b64decode(
    b'aHR0cHM6Ly93d3cudWx0aW1hdGUtZ3VpdGFyLmNvbQ=='
).decode()

COLUMN_SEPARATOR = 4
CNT = 0
BGS = LoopedList('black', '')


def next_bg():
    global CNT
    CNT += 1
    return BGS[CNT]

class DictObj(object):

    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)

    @property
    def date(self):
        if self.__date == "?":
            return self.__date
        return datetime.utcfromtimestamp(
            int(self.__date)
        ).strftime('%d%b%Y')

    @date.setter
    def date(self, d):
        self.__date = d


def retro(*args, **kwargs):
    return echo(*args, **kwargs, mode='retro')


def get_page_data(query, page=1):
    url = '{}/search.php?search_type=title&value={}&page={}'.format(
        MAIN_URL,
        quote(query),
        page
    )
    return ultimateultimateguitar.get_data(url)

def sort_by_artist(results):
    _ = {
        # 'Sting': 1, 'U2: 34,
    }
    for r in results:
        if r['artist_name'] not in _.keys():
            _[r['artist_name']]  = 1
        else:
            _[r['artist_name']] += 1

    return [ DictObj( **{'artist_name': k, 'songs': v} ) for k, v in _.items() ]


def filter_by_artist(results, selected):
    return [
        DictObj(**r) for r in results if r['artist_name'] == selected.artist_name
    ]

def interact(max=1, message=''):
    try:
        i = input(message)
        i = i.strip().upper()
        i = int(i)
        if i and i <= max:
            print()
            return int(i) - 1
        return interact(max=max)
    except ValueError:
        return interact(max=max)



class AutoTui(object):

    ID = 'Id'

    def __init__(self, rows=[], cols=[], safe_width=0):

        self.cols = cols

        self.rows = []
        self.rows = self.convert_to_objects(rows)
        self.discard_rows()

        self.safe_width = safe_width

        self.calculate_max_lens()

        retro( self.titles_row() )
        for r in self.objects_rows():
            retro( r )


    @property
    def id_size(self):
        return length_pad(self.rows) if length_pad(self.rows) > len(self.ID) else len(self.ID)

    @property
    def tui_width(self):
        w = self.id_size
        for col in self.cols:
            w += COLUMN_SEPARATOR + col.max_len
        return w

    def convert_to_objects(self, objs):
        objects = []
        for obj in objs:
            if type(obj) == dict:
                obj = DictObj(**obj)
            objects.append(obj)
        return objects


    def discard_rows(self):

        del_indeces = []

        for x, obj in enumerate(self.rows):

            for field in self.cols:

                try:
                    field_value = getattr(obj, field.key)

                except AttributeError:
                    setattr(obj, field.key, '?')
                    field_value = getattr(obj, field.key)

                if field_value in field.ignore:
                    del_indeces.append(x)
                    break

        # del rows from biggest index to smallest
        # to avoid issues with changing length
        for i in reversed(del_indeces):
            del self.rows[i]



    def calculate_max_lens(self):
        ''' takes a list of objects|dicts and builds an array
            of the longest len value for each specified obj.attr

            if a key title is longer than it's longest value,
            that length is stored in the returned dictionary.
        '''
        for obj in self.rows:

            for field in self.cols:

                try:

                    field_value = getattr(obj, field.key)
                    # if field_value in field.ignore:
                    #     continue

                    if len(str(field_value)) > field.max_len:
                        field.max_len = len(str(field_value))

                except AttributeError:
                    pass

        # if self.safe_width:

        #     if sum(
        #         [ f.max_len for f in self.cols ]
        #     ) + COLUMN_SEPARATOR * ( len(self.cols) -1 ) > tty_cols():

        #         longest_f = ''
        #         longest_l = 0

        #         for field in self.cols:
        #             if field.max_len > longest_l:
        #                 longest_f = field
        #                 longest_l = field.max_len

        #         for field in self.cols:
        #             if field.title == longest_f.title:
        #                 field.max_len = 0 # make adaptable size
        #                 break


    def titles_row(self):

        r = Row()

        r.append(
            FString(
                self.ID,
                size=self.id_size + COLUMN_SEPARATOR,
                fg='black',
                bg='white',
                align='l',
                fx=['underline', ''],
            ),
        )

        for col in self.cols:

            r.append(
                FString(
                    col.title,
                    size=col.max_len + COLUMN_SEPARATOR if col.max_len else col.max_len,
                    fg='black',
                    bg='white',
                    fx=['underline', ''],
                    align=col.align,
                )
            )

        return r


    def objects_rows(self):

        for i, row in enumerate(self.rows):

            bg = next_bg()
            r = Row()
            r.append(
                FString(
                    '{:0{}d}'.format(i +1, self.id_size),
                    size=self.id_size + COLUMN_SEPARATOR,
                    fg='cyan',
                    bg=bg,
                    align='l',
                ),
            )

            for col in self.cols:

                field_value = getattr(row, col.key)

                r.append(
                    FString(
                        field_value,
                        size=col.max_len + COLUMN_SEPARATOR,
                        fg='red' if field_value == '?' else '',
                        bg=bg,
                        align=col.align,
                    ),
                )

            yield r


    def selection(self, message):
        # retro(message, 'yellow')

        r = Row(
            FString(
                message,
                size=self.tui_width,
                fg='black',
                bg='white',
                fx=['underline', ''],
                align='l',
            )
        ).echo('raw')

        return self.rows[
            interact(max=len(self.rows))
        ]


def length_pad(l):
    ''' return amount of zeros needed to pad amount of items in l '''
    return len(
        str( len(l) )
    )



def search_ug(query):

    echo('Searching Pages: ', mode='raw')
    results = []
    for p in range(1, 11):

        # DO NOT FOLLOW RE-DIRECTS...
        data = get_page_data(query, page=p)
        if not data:
            break

        data = data['store']['page']['data']

        if not len(data['results']):
            break

        echo('{}, '.format(p), mode='raw')
        results.extend(
            data['results']
        )
    
    echo('done!')
    return results



class Field(object):

    def __init__(self, k, title, ignore_values=[], align='l'):
        self.key = k
        self.title = title
        self.max_len = len(title)
        self.align = align
        self.ignore = ignore_values



if __name__ == '__main__':

    rc = -1
    SEARCH_QUERY = ' '.join(sys.argv[1:])
    results = search_ug(SEARCH_QUERY)
    if not results or not len(results):
        raise Exception

    FString(
        '"{}": {} tabs reported - {} tabs found'.format(
            SEARCH_QUERY.title(),
            999,
            len(results),
        ),
        fg='magenta',
        fx=['reverse'],
    ).echo('retro')


    selected_artist = AutoTui(
        rows = sort_by_artist(results),
        cols = [
            Field('artist_name', 'Artist'),
            Field('songs', 'Tabs', align='r'),
        ],
    ).selection('Choose an Artist:')


    FString(
        selected_artist.artist_name,
        fg='magenta'
    ).echo('retro')


    selected_song = AutoTui(
        rows = filter_by_artist(results, selected_artist),
        cols = [
            Field('type', 'Type', ignore_values=['Pro', 'Video']),
            Field('date', 'Date'),
            Field('song_name', 'Songs'),
            Field('tonality_name', 'Key', align='r'),
            Field('rating', 'Rating', align='r'),
            Field('votes', 'Votes', align='r'),
            Field('status', 'Status', align='c'),
            Field('tab_access_type', 'Access', align='r'),
        ],
    ).selection('Choose a Tab:')

    transpose = 0
    if selected_song.tonality_name:
        try:
            transpose = int(
                input(f'Transpose from {selected_song.tonality_name} ? ')
            )
        except:
            pass

    ultimateultimateguitar.main(
        url=selected_song.tab_url,
        transpose=transpose,
    )

    print()

    if selected_song.version_description:
        retro(
            'Description: \n{}'.format(
                selected_song.version_description,
            ), 'blue'
        )

    retro(
        '\nSong Url: \n{}'.format(
            selected_song.tab_url,
        ), 'magenta'
    )

    rc = 0