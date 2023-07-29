from pynostr.event import Event


def code_review(event: Event):
    print(event.content)
    return "OK"
