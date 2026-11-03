"""Shared, bounded scope for optional external collectors."""
HARVESTER_SOURCES=('crtsh','certspotter','duckduckgo','otx','urlscan','github-code','rapiddns')
MAIGRET_SITES={'GitHub':('github.com','www.github.com','api.github.com'),'Reddit':('reddit.com','www.reddit.com','old.reddit.com'),
               'Steam':('steamcommunity.com',),'GitLab':('gitlab.com',),'Twitch':('twitch.tv','www.twitch.tv'),
               'Pinterest':('pinterest.com','www.pinterest.com'),'TikTok':('tiktok.com','www.tiktok.com'),
               'Instagram':('instagram.com','www.instagram.com'),'VSCO':('vsco.co',),'Medium':('medium.com',)}
DEFAULT_MAIGRET_SITES=['GitHub','Reddit','Steam']

def selected(values,allowed,maximum):
    if not isinstance(values,list) or not values or len(values)>maximum or any(not isinstance(v,str) or v not in allowed for v in values):
        raise ValueError('Choose a bounded list of supported sources/sites.')
    return list(dict.fromkeys(values))
