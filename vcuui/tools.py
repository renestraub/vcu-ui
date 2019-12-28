
def secs_to_hhmm(secs):
    t = int((secs+30) / 60)
    h = int(t / 60)
    m = int(t % 60)
    return h, m
