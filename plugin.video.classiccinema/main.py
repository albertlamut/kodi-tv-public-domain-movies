import sys, os, json, urllib.parse
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE = sys.argv[0]
DATA = os.path.join(os.path.dirname(__file__), 'resources', 'movies.json')
MOVIES = json.load(open(DATA, encoding='utf-8'))
FAV_PATH = os.path.join(xbmc.translatePath(ADDON.getAddonInfo('profile')), 'favorites.json') if hasattr(xbmc, 'translatePath') else os.path.join(__import__('xbmcvfs').translatePath(ADDON.getAddonInfo('profile')), 'favorites.json')

def favorites():
    try:
        with open(FAV_PATH, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return []

def save_favorites(ids):
    os.makedirs(os.path.dirname(FAV_PATH), exist_ok=True)
    with open(FAV_PATH, 'w', encoding='utf-8') as f: json.dump(ids, f)

def uri(**kw): return BASE + '?' + urllib.parse.urlencode(kw)

def folder(label, **kw):
    item = xbmcgui.ListItem(label=label)
    xbmcplugin.addDirectoryItem(HANDLE, uri(**kw), item, True)

def film(m):
    playable = bool(m.get('url'))
    label = '{} ({}){}'.format(m['title'], m['year'], '' if playable else ' [catalogue only]')
    item = xbmcgui.ListItem(label=label)
    item.setArt({'poster':m.get('poster',''), 'thumb':m.get('poster','')})
    item.setInfo('video', {'title':m['title'], 'year':m['year'], 'plot':m.get('plot') or ('Streaming link pending verification.' if not playable else 'Classic film. Source: Internet Archive.')})
    item.setProperty('IsPlayable', 'true' if playable else 'false')
    if m.get('awards'):
        awards_text = '\n'.join('{} {} - {}: {} ({})'.format(a['award'], a['ceremony_year'], a['category'], a['status'], a.get('credit','')) for a in m['awards'])
        item.setInfo('video', {'title':m['title'], 'year':m['year'], 'plot':(m.get('plot') or '') + '\n\nAwards & nominations:\n' + awards_text})
    context_label = 'Remove favorite' if m['id'] in favorites() else 'Add favorite'
    item.addContextMenuItems([(context_label, 'RunPlugin('+uri(action='favorite', id=m['id'])+')')])
    xbmcplugin.addDirectoryItem(HANDLE, uri(action='play' if playable else 'info', id=m['id']), item, False)

def listing(items):
    for m in sorted(items, key=lambda x: x['title'].casefold().removeprefix('the ')): film(m)
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE)

AWARDS = ['Academy Awards (Oscars)', 'Golden Globes', 'BAFTA Film Awards', 'Cannes Film Festival', 'Venice Film Festival']

def matching_awards(m, award, year=None, category=None, status=None):
    return [a for a in m.get('awards', []) if a['award'] == award and (year is None or a['ceremony_year'] == year) and (category is None or a['category'] == category) and (status is None or a['status'] == status)]

def award_folders(entries, key, action, award, year=None):
    for v in sorted(set(a[key] for a in entries)):
        kw = {'action':action, 'award':award, 'value':v}
        if year is not None: kw['year']=year
        folder(str(v), **kw)
    xbmcplugin.endOfDirectory(HANDLE)

def main():
    folder('All movies A-Z', action='all')
    folder('By year', action='years')
    folder('By decade', action='decades')
    folder('Search', action='search')
    folder('Favorites', action='favorites')
    folder('Available to watch', action='available')
    for award in AWARDS: folder(award, action='award_years', award=award)
    xbmcplugin.endOfDirectory(HANDLE)

def run():
    q = dict(urllib.parse.parse_qsl(sys.argv[2].lstrip('?')))
    action = q.get('action', 'home')
    if action == 'home': main()
    elif action == 'all': listing(MOVIES)
    elif action == 'available': listing([m for m in MOVIES if m['url']])
    elif action == 'favorites': listing([m for m in MOVIES if m['id'] in favorites()])
    elif action == 'award_years':
        award = q['award']
        entries = [a for m in MOVIES for a in matching_awards(m, award)]
        if not entries:
            folder('No verified awards in catalogue yet', action='empty')
            xbmcplugin.endOfDirectory(HANDLE)
        else:
            award_folders(entries, 'ceremony_year', 'award_year', award)
    elif action == 'award_year':
        award, year = q['award'], int(q['value'])
        folder('Browse by category', action='award_categories', award=award, year=year)
        folder('Winners', action='award_status', award=award, year=year, status='Winner')
        folder('Nominees', action='award_status', award=award, year=year, status='Nominee')
        xbmcplugin.endOfDirectory(HANDLE)
    elif action == 'award_categories':
        award, year = q['award'], int(q['year'])
        entries = [a for m in MOVIES for a in matching_awards(m, award, year)]
        award_folders(entries, 'category', 'award_category', award, year)
    elif action == 'award_category':
        award, year, category = q['award'], int(q['year']), q['value']
        listing([m for m in MOVIES if matching_awards(m, award, year, category)])
    elif action == 'award_status':
        award, year, status = q['award'], int(q['year']), q['status']
        listing([m for m in MOVIES if matching_awards(m, award, year, status=status)])
    elif action == 'empty':
        xbmcgui.Dialog().notification('Classic Cinema', 'No verified titles yet')
        xbmcplugin.endOfDirectory(HANDLE)
    elif action == 'years':
        for y in sorted(set(m['year'] for m in MOVIES)): folder(str(y), action='year', value=y)
        xbmcplugin.endOfDirectory(HANDLE)
    elif action == 'decades':
        for d in sorted(set(m['year']//10*10 for m in MOVIES)): folder('{}s'.format(d), action='decade', value=d)
        xbmcplugin.endOfDirectory(HANDLE)
    elif action == 'year': listing([m for m in MOVIES if m['year']==int(q['value'])])
    elif action == 'decade': listing([m for m in MOVIES if m['year']//10*10==int(q['value'])])
    elif action == 'search':
        keyboard = xbmc.Keyboard('', 'Search movie title'); keyboard.doModal()
        if keyboard.isConfirmed(): listing([m for m in MOVIES if keyboard.getText().casefold() in m['title'].casefold()])
        else: xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'favorite':
        mid = int(q['id']); ids = favorites()
        if mid in ids: ids.remove(mid)
        else: ids.append(mid)
        save_favorites(ids); xbmc.executebuiltin('Container.Refresh')
    elif action in ('play','info'):
        m = next((m for m in MOVIES if m['id']==int(q['id'])), None)
        if m and action=='play' and m['url']:
            item = xbmcgui.ListItem(path=m['url']); item.setProperty('IsPlayable','true')
            item.setInfo('video', {'title':m['title'], 'year':m['year'], 'plot':m.get('plot', '')})
            xbmcplugin.setResolvedUrl(HANDLE, True, item)
        else:
            xbmcgui.Dialog().ok('Classic Cinema', 'No verified streaming link available for this title yet.')
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

if __name__ == '__main__': run()
