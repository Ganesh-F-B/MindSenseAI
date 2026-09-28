import re

def _is_deescalation(text):
    t = text.lower()
    t = re.sub(r"['’`]", "", t)
    t_norm = re.sub(r"[^\w\s]", " ", t)
    t_norm = re.sub(r"\s+", " ", t_norm).strip()
    deescalation_patterns = [
        r"\b(?:i\s+am|im)\s+(?:safe|fine|okay|alright|doing\s+okay|feeling\s+better|much\s+better)\b",
        r"\b(?:yes|yeah|yep|sure)\s*,?\s*(?:i\s+am|im)\s+safe\b",
        r"\b(?:no|nope)\s*,?\s*(?:i\s+am|im)\s+safe\b",
        r"\b(?:no|nope)\s*,?\s*(?:i\s+am|im)\s+not\s+(?:going\s+to|gonna)\s+(?:do\s+it|hurt\s+myself|harm\s+myself|kill\s+myself)\b",
        r"\b(?:i\s+)?am\s+in\s+a\s+safe\s+place\b",
        r"\b(?:safe\s+right\s+now|safe\s+here|currently\s+safe)\b",
        r"\b(?:please\s+)?(?:dont|do\s+not)\s+send\s+(?:anyone|anybody|help|an?\s+alert|police)\b",
        r"\b(?:i\s+)?(?:want|wanna)\s+things\s+to\s+get\s+better\b",
        r"\bi\s+(?:will|gonna)\s+be\s+okay\b",
        r"\b(?:i\s+am|im)\s+not\s+(?:going\s+to|gonna)\s+(?:hurt|harm|kill)\s+myself\b",
        r"\b(?:dont|do\s+not|never|wont|will\s+not)\s+want\s+to\s+die\b",
        r"\b(?:i\s+)?want\s+to\s+(?:live|keep\s+living|survive|stay\s+alive)\b",
        r"\b(?:i\s+)?will\s+not\s+die\b",
        r"\b(?:i\s+)?wont\s+die\b",
        r"\b(?:i\s+am|im)\s+not\s+suicidal\b",
        r"\bno\s+imminent\s+danger\b",
        r"\bnot\s+going\s+to\s+hurt\s+myself\b",
    ]
    return any(re.search(p, t_norm) for p in deescalation_patterns)

def _is_imminent(text):
    t = text.lower()
    t = re.sub(r"['’`]", "", t)
    t_norm = re.sub(r"[^\w\s]", " ", t)
    t_norm = re.sub(r"\s+", " ", t_norm).strip()
    imminent_patterns = [
        r"\b(?:going to|gonna|about to|will|planning to)\s+(?:kill|end|hurt|harm|slit|hang|overdose|shoot)\s+(?:myself|my life)\b",
        r"\b(?:kill|end|hurt|harm)\s+myself\s+(?:right\s+now|now|today|tonight|immediately|this\s+second|this\s+moment)\b",
        r"\b(?:taking|swallowing|downing|drank|drinking)\s+(?:all\s+the\s+)?(?:pills|poison|medicine|tablets)\b",
        r"\b(?:have|got)\s+(?:the\s+)?(?:pills|poison|medicine|tablets|knife|blade|gun|rope)\b.*\b(?:taking|swallowing|downing|using)\s+them\b",
        r"\b(?:taking|swallowing|downing)\s+(?:them|the\s+pills|all\s+the\s+pills|pills|poison)\s+(?:now|right\s+now|today|tonight)\b",
        r"\b(?:have|got)\s+(?:the\s+)?(?:pills|knife|gun|rope|blade)\s+(?:in\s+(?:my\s+)?hand|ready|with\s+me)\b",
        r"\b(?:about\s+to|going\s+to|gonna|ready\s+to)\s+jump\b",
        r"\b(?:this\s+is\s+my\s+)?(?:final|last)\s+(?:goodbye|farewell|message|note)\b",
        r"\bgoodbye\s+(?:everyone|all|cruel\s+world|forever)\b",
        r"\b(?:i\s+am|im)\s+ending\s+it\s+(?:all\s+)?(?:right\s+now|now|today|tonight)\b",
        r"\b(?:i\s+am|im)\s+doing\s+it\s+(?:right\s+now|now|today|tonight)\b",
    ]
    return any(re.search(p, t_norm) for p in imminent_patterns)

def _is_historical(text):
    t = text.lower()
    t = re.sub(r"['’`]", "", t)
    t_norm = re.sub(r"[^\w\s]", " ", t)
    t_norm = re.sub(r"\s+", " ", t_norm).strip()
    past_markers = r"\b(?:felt\s+like\s+dying|felt\s+like|was\s+feeling|had\s+(?:suicidal\s+thoughts|thoughts\s+of\s+dying)|used\s+to|was\s+suicidal|earlier\s+today|yesterday|previously|last\s+(?:week|month|year))\b"
    current_coping = r"\b(?:better|fine|okay|alright|recovering|safe|doing\s+well|in\s+control|under\s+control|things\s+under\s+control|handled\s+it|past\s+it|moved\s+on)\b"
    if re.search(past_markers, t_norm) and re.search(current_coping, t_norm):
        return True
    if re.search(r"\b(?:felt\s+like\s+dying\s+earlier|was\s+suicidal\s+before|used\s+to\s+want\s+to\s+die|used\s+to\s+be\s+suicidal)\b", t_norm):
        return True
    return False

print("DE-ESCALATION:")
cases_b = ['i will not die', 'i am safe right now', 'i want things to get better', "please don't send anyone", 'no i am safe']
for c in cases_b:
    print(f"  {c!r}: {_is_deescalation(c)}")

print("\nIMMINENT:")
cases_d = ['i am going to hurt myself right now', 'i have the pills and i am taking them right now', 'i am about to jump']
for c in cases_d:
    print(f"  {c!r}: {_is_imminent(c)}")

print("\nHISTORICAL:")
cases_e = ['i felt like dying earlier today, but i am better now', 'i had suicidal thoughts last year, but i am doing well now', 'used to be suicidal, but now things are under control']
for c in cases_e:
    print(f"  {c!r}: {_is_historical(c)}")
