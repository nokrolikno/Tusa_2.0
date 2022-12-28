
def parse_url(url: str):
    url = url.strip()
    parsed_url = url.split('/')
    return {'album': parsed_url[-3], 'track': parsed_url[-1]}


def try_get_url(text: str):
    url = text.split('?')[0].strip()
    return url

