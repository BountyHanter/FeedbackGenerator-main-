def pluralize_comments(count):
    if 11 <= count % 100 <= 19:
        return f"{count} комментариев"
    elif count % 10 == 1:
        return f"{count} комментарий"
    elif 2 <= count % 10 <= 4:
        return f"{count} комментария"
    else:
        return f"{count} комментариев"
