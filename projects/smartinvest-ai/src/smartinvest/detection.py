"""Explainable local rules only: NOT a fraud verdict, model, or FCA lookup.

Important: We intentionally do NOT fetch user-provided URLs; this also avoids SSRF.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import ipaddress
import re
from urllib.parse import urlsplit

ENGINE_VERSION = "0.3.0"

FCA_FIRM_CHECKER = "https://www.fca.org.uk/consumers/fca-firm-checker"
FCA_WARNINGS = "https://www.fca.org.uk/consumers/warning-list-unauthorised-firms"


@dataclass(frozen=True)
class Finding:
    code: str
    category: str
    severity: str
    explanation: str
    evidence: str


@dataclass(frozen=True)
class ScreeningResult:
    screening_status: str
    verification_status: str
    findings: list[Finding]
    claimed_firm: str
    websites: list[str]
    next_steps: list[str]
    limitations: list[str]
    engine_version: str = ENGINE_VERSION
    schema_version: str = "1"

    def as_dict(self) -> dict:
        return asdict(self)


# Each indicator is independently explainable. No opaque fake "fraud probability".
RULES = [
    (
        "GUARANTEED_RETURNS", "investment_claim", "high",
        re.compile(
            r"\b(?:guaranteed?|guarantees?)\b.{0,60}?\b(?:returns?|profits?|income|earnings)\b"
            r"|\b(?:returns?|profits?|income|earnings)\b.{0,60}?\bguaranteed?\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "The offer appears to promise guaranteed investment returns.",
    ),
    (
        "NO_RISK_CLAIM", "investment_claim", "high",
        re.compile(r"\b(?:risk[ -]?free|zero[ -]?risk|no[ -]?risk|can['’]?t lose)\b", re.I),
        "The offer implies money cannot be lost. Investments can carry risk.",
    ),
    (
        "URGENCY", "pressure", "medium",
        re.compile(r"\b(?:act now|last chance|limited time|today only|offer expires|immediately)\b", re.I),
        "The offer uses time pressure. Pressure alone does not prove fraud.",
    ),
    (
        "PRIVATE_MESSAGING", "contact_channel", "low",
        re.compile(r"\b(?:whatsapp|telegram)\b", re.I),
        "The offer mentions private messaging. This is not inherently suspicious.",
    ),
    (
        "SEND_TO_WALLET", "payment", "medium",
        re.compile(r"\b(?:send|transfer)\s+(?:your\s+)?(?:money|funds|payment|crypto|bitcoin|btc)\s+to\s+(?:this|my|a|the)\s+(?:wallet|account)\b", re.I),
        "The offer directs money to a wallet or account. Verify the beneficiary independently.",
    ),
]

# High recurring returns are warning signs, but annual return statements by
# themselves are not given this indicator.
RECURRING_RETURN_RE = re.compile(
    r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*%\s*(?:a |per |every )?\s*(day|daily|week|weekly|month|monthly)\b",
    re.IGNORECASE,
)
WEB_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
URL_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly"}


def _excerpt(text: str, match: re.Match[str], length: int = 120) -> str:
    excerpt = " ".join(text[max(0, match.start() - 25):min(len(text), match.end() + 35)].split())
    return WEB_RE.sub(lambda m: _redact_credentials(m.group()), excerpt)[:length]


def _negated_claim(text: str, match: re.Match[str]) -> bool:
    """Narrow explicit-negation heuristic, not a language-understanding model."""
    prefix = re.split(r"[.!?;\n]|\b(?:but|however|yet)\b", text[:match.start()], flags=re.I)[-1][-70:]
    # 'not only guaranteed' is an affirmative pitch, not a denial.
    if re.search(r"\bnot\s+(?:only|just)\s*$", prefix, re.I):
        return False
    modifiers = r"(?:a|an|any|entirely|completely|actually|necessarily|truly|ever|be|is|are|offer|promise|claim|trust)"
    if re.search(r"\b(?:not|never|no)\s+(?:" + modifiers + r"\s+){0,3}$", prefix, re.I):
        return True
    return bool(re.search(r"\b(?:not|never)\s+(?:(?:be|ever|necessarily|actually)\s+){0,2}guaranteed?\b", match.group(), re.I))


def _redact_credentials(raw_url: str) -> str:
    # Mask user-info without visiting the URL. Keep the real destination visible.
    return re.sub(r"^((?:https?://)?)[^/\s]*@", r"\1[redacted]@", raw_url, flags=re.I)


def _extract_urls(text: str, url_input: str) -> list[str]:
    entries = ([url_input.strip()] if url_input.strip() else []) + WEB_RE.findall(text)
    # Stable de-duplication; no remote fetches or DNS resolution.
    return list(dict.fromkeys(item.rstrip(",.;)") for item in entries if item))[:10]


def _url_findings(raw_url: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in raw_url) or "\\" in raw_url:
            raise ValueError("Whitespace/control characters or ambiguous backslash")
        url = raw_url if "://" in raw_url else "https://" + raw_url
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host or parsed.scheme not in ("http", "https"):
            raise ValueError("invalid URL")
        _ = parsed.port  # urlsplit otherwise leaves invalid/out-of-range ports unchecked.
        try:
            ipaddress.ip_address(host)
        except ValueError:
            host = host.encode("idna").decode("ascii")
            if len(host) > 253 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in host.split(".")):
                raise ValueError("Invalid hostname")
    except (ValueError, UnicodeError):
        return [Finding(
            "INVALID_URL", "website", "low", "Could not parse this website address; verify it manually.", _redact_credentials(raw_url)[:120]
        )]

    if parsed.username or parsed.password:
        findings.append(Finding(
            "URL_CREDENTIALS", "website", "medium",
            "The URL includes an @-style user-info section that can disguise its real destination.",
            "[userinfo redacted]@" + host,
        ))
    if parsed.scheme == "http":
        findings.append(Finding(
            "HTTP_NO_ENCRYPTION", "website", "low",
            "The URL uses HTTP, not HTTPS. HTTPS does not itself prove legitimacy.", _redact_credentials(raw_url)[:120]
        ))
    if host.startswith("xn--") or ".xn--" in host:
        findings.append(Finding(
            "PUNYCODE_DOMAIN", "website", "low",
            "The domain uses punycode encoding. Check the spelling carefully; this can be legitimate.", host
        ))
    if host in URL_SHORTENERS:
        findings.append(Finding(
            "SHORTENED_URL", "website", "low",
            "This shortened URL obscures the destination. Avoid assuming it is safe.", host
        ))
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        findings.append(Finding(
            "IP_ADDRESS_URL", "website", "low",
            "The URL points directly to an IP address rather than a named domain.", host
        ))
    return findings


def scan_offer(
    offer_text: str = "", website_url: str = "", claimed_firm: str = ""
) -> ScreeningResult:
    """Screen a user-supplied investment offer locally. Does not verify firms or URLs."""
    if not isinstance(offer_text, str) or not isinstance(website_url, str) or not isinstance(claimed_firm, str):
        raise TypeError("Inputs must be strings")
    if not (offer_text.strip() or website_url.strip()):
        raise ValueError("Provide an offer message or website address")
    if len(offer_text) > 10_000 or len(website_url) > 2_048 or len(claimed_firm) > 200:
        raise ValueError("Input exceeds allowed length")

    findings: list[Finding] = []
    for code, category, severity, pattern, explanation in RULES:
        for match in pattern.finditer(offer_text):
            if code in {"GUARANTEED_RETURNS", "NO_RISK_CLAIM"} and _negated_claim(offer_text, match):
                continue
            findings.append(Finding(code, category, severity, explanation, _excerpt(offer_text, match)))
            break  # One finding per indicator, using the first affirmative match.

    for recurring in RECURRING_RETURN_RE.finditer(offer_text):
        percent = float(recurring.group(1).replace(",", "."))
        period = recurring.group(2).lower()
        threshold = 5 if period in ("month", "monthly") else 2 if period in ("week", "weekly") else 1
        if percent >= threshold and not _negated_claim(offer_text, recurring):
            findings.append(Finding(
                "HIGH_RECURRING_RETURN", "investment_claim", "high",
                "The offer advertises a high recurring percentage return. Check claims independently.",
                _excerpt(offer_text, recurring),
            ))
            break

    urls = _extract_urls(offer_text, website_url)
    for url in urls:
        findings.extend(_url_findings(url))

    status = "warning_signals_detected" if findings else "no_configured_indicators_detected"
    return ScreeningResult(
        screening_status=status,
        verification_status="not_checked",
        findings=findings,
        claimed_firm=claimed_firm.strip(),
        websites=[_redact_credentials(url) for url in urls],
        next_steps=[
            "Do not transfer money based solely on an unfamiliar investment offer.",
            f"Check the firm and its permissions independently: {FCA_FIRM_CHECKER}",
            f"Review official warnings: {FCA_WARNINGS}",
            "Compare the website, email and phone details with independent official sources.",
            "If you have already paid, contact your bank promptly and report the incident.",
        ],
        limitations=[
            "This is an educational, rule-based screening, not a fraud determination.",
            "No live FCA, domain, company or payment verification was performed.",
            "No warning matches does not mean an offer is safe or legitimate.",
            "Negation, quotations, sarcasm, obfuscated wording and ambiguous context can still be misread.",
            "Recurring-return thresholds are manually chosen warning heuristics, not estimated fraud probabilities.",
        ],
    )
