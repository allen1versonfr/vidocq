"""SauceNAO adapter: local files only, no remote thumbnails or source visits."""
import base64
import binascii
import io
import json
import math
import re
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener

MAX_IMAGE=5*1024*1024
ENDPOINT='https://saucenao.com/search.php'

class NoUploadRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('SauceNAO redirected the upload. Redirects are blocked; no image or API key was forwarded.')


def prepare_image(encoded):
    if not isinstance(encoded,str) or len(encoded)>7_000_000:
        raise ValueError('Choose a PNG, JPEG, or WebP image up to 5 MB.')
    try:raw=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError):raise ValueError('Invalid image upload.')
    if not raw or len(raw)>MAX_IMAGE:raise ValueError('Image must be between 1 byte and 5 MB.')
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError:
        raise ValueError('Image search requires Pillow. Run the launcher again to install the updated requirements.')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ('JPEG','PNG','WEBP'):raise ValueError('Only PNG, JPEG, and WebP images are supported.')
            if image.width*image.height>20_000_000:raise ValueError('Image exceeds the 20-megapixel limit. Resize it first.')
            if getattr(image,'is_animated',False):raise ValueError('Use a still image, not an animation.')
            image=ImageOps.exif_transpose(image)
            image.thumbnail((1800,1800))
            if image.mode in ('RGBA','LA') or 'transparency' in image.info:
                rgba=image.convert('RGBA');canvas=Image.new('RGB',rgba.size,'white');canvas.paste(rgba,mask=rgba.getchannel('A'))
            else:canvas=image.convert('RGB')
            # A clean pixel copy prevents source EXIF, comments, and ICC data from carrying over.
            clean=Image.new('RGB',canvas.size);clean.paste(canvas)
            out=io.BytesIO();clean.save(out,format='JPEG',quality=90)
            result=out.getvalue()
            if len(result)>MAX_IMAGE:raise ValueError('Prepared image is too large. Resize it first.')
            return result
    except ValueError:raise
    except Exception:raise ValueError('The image could not be decoded safely. Try a different PNG, JPEG, or WebP file.')


def multipart(image,key):
    boundary='Vidocq'+secrets.token_hex(20)
    chunks=[]
    for name,value in [('api_key',key),('output_type','2'),('db','999'),('numres','16')]:
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="query.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()+image+b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode())
    return boundary,b''.join(chunks)


def parse_response(data):
    if not isinstance(data,dict) or not isinstance(data.get('header'),dict):raise ValueError('SauceNAO returned an unexpected response.')
    header=data['header']
    try:status=int(header.get('status',-1))
    except (TypeError,ValueError):raise ValueError('SauceNAO returned an invalid status.')
    if status!=0:
        # Do not echo provider messages: they can contain submitted data or secrets.
        raise ValueError('SauceNAO could not complete the search. Check your API key, account quota, and service availability.')
    rows=[]
    for item in (data.get('results') or [])[:16]:
        h=item.get('header',{});d=item.get('data',{})
        try:similarity=float(h.get('similarity',0))
        except (ValueError,TypeError):similarity=0
        if not math.isfinite(similarity):similarity=0
        similarity=max(0,min(similarity,100))
        urls=[]
        for url in d.get('ext_urls',[]) or []:
            if not isinstance(url,str):continue
            try:
                p=urlparse(url)
                if p.scheme in ('http','https') and p.hostname and not p.username and not p.password:urls.append(url[:2000])
            except ValueError:continue
        author=d.get('member_name') or d.get('creator') or d.get('author_name') or 'Not listed'
        title=d.get('title') or d.get('eng_name') or d.get('jp_name') or d.get('source') or 'Possible image source'
        rows.append({'title':str(title)[:500],'similarity':similarity,'index':str(h.get('index_name','Unknown index'))[:200],'author':str(author)[:500],'sources':urls[:5]})
    rows.sort(key=lambda x:x['similarity'],reverse=True)
    return {'provider':'SauceNAO','rows':rows,'quota':{'short_remaining':header.get('short_remaining'),'long_remaining':header.get('long_remaining')},'notice':'Similarity is a provider score, not proof of identity or original authorship. Source URLs are text only. No thumbnails or source pages were fetched.'}


def search_image(payload):
    if payload.get('consent') is not True:raise ValueError('Confirm that this image may be sent to SauceNAO before searching.')
    key=payload.get('api_key','')
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{20,128}',key.strip()):raise ValueError('Enter your SauceNAO API key in the image-search tab.')
    prepared=prepare_image(payload.get('image'))
    boundary,body=multipart(prepared,key.strip())
    request=Request(ENDPOINT,data=body,method='POST',headers={'Content-Type':'multipart/form-data; boundary='+boundary,'Accept':'application/json','User-Agent':'Vidocq/2.2.1'})
    try:
        # API key stays in the HTTPS request body. Redirects never forward it.
        with build_opener(NoUploadRedirect).open(request,timeout=25) as response:
            raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('SauceNAO response exceeded the size limit.')
        try:data=json.loads(raw)
        except (ValueError,UnicodeError):raise ValueError('SauceNAO returned a non-JSON response. It may be unavailable or require verification in its own website.')
        return parse_response(data)
    except HTTPError as error:
        if error.code==429:raise ValueError('SauceNAO rate limit reached. Wait before trying again; check your account quota.')
        if error.code in (401,403):raise ValueError('SauceNAO denied the request. Check your API key and account access.')
        raise ValueError('SauceNAO returned HTTP '+str(error.code)+'. Try again later.')
    except (URLError,TimeoutError,OSError):raise ValueError('SauceNAO could not be reached. Check your connection and try again later.')
