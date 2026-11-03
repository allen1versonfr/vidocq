"""Offline numbering-plan metadata; no calls, SMS, account or owner lookups."""
import re
import phonenumbers as pn
from phonenumbers import carrier, geocoder, timezone

TYPES={pn.PhoneNumberType.FIXED_LINE:'Fixed line',pn.PhoneNumberType.MOBILE:'Mobile',pn.PhoneNumberType.FIXED_LINE_OR_MOBILE:'Fixed line or mobile',pn.PhoneNumberType.TOLL_FREE:'Toll free',pn.PhoneNumberType.PREMIUM_RATE:'Premium rate',pn.PhoneNumberType.SHARED_COST:'Shared cost',pn.PhoneNumberType.VOIP:'VoIP',pn.PhoneNumberType.PERSONAL_NUMBER:'Personal number',pn.PhoneNumberType.PAGER:'Pager',pn.PhoneNumberType.UAN:'Universal access',pn.PhoneNumberType.VOICEMAIL:'Voicemail',pn.PhoneNumberType.UNKNOWN:'Unknown'}
NOTICE='Offline numbering-plan metadata only. Valid format does not prove that a number is assigned, reachable, current, or owned by the subject. Region and carrier describe allocations, not live location or necessarily the current carrier.'

def inspect_phone(value,region='US'):
    if not isinstance(value,str) or not value.strip() or len(value)>80 or any(ord(c)<32 for c in value):raise ValueError('Enter a phone number of 1–80 characters.')
    region=str(region).upper().strip()
    if not value.strip().startswith('+') and region not in pn.SUPPORTED_REGIONS:raise ValueError('Use a supported two-letter phone region such as US, GB, or CA.')
    try:number=pn.parse(value.strip(),None if value.strip().startswith('+') else region)
    except pn.NumberParseException:raise ValueError('Could not parse that phone number. Include its country calling code or choose the correct region.') from None
    if number.extension:raise ValueError('Enter the main phone number without an extension.')
    if not pn.is_possible_number(number):raise ValueError('This number does not have a possible length for its numbering plan.')
    return {'e164':pn.format_number(number,pn.PhoneNumberFormat.E164),'international':pn.format_number(number,pn.PhoneNumberFormat.INTERNATIONAL),
        'national':pn.format_number(number,pn.PhoneNumberFormat.NATIONAL),'country_calling_code':number.country_code,
        'region_code':pn.region_code_for_number(number) or 'Unknown','number_type':TYPES.get(pn.number_type(number),'Unknown'),
        'valid_numbering_plan':pn.is_valid_number(number),'allocation_region':geocoder.description_for_number(number,'en') or 'Not available',
        'original_carrier':carrier.name_for_number(number,'en') or 'Not available','time_zones':list(timezone.time_zones_for_number(number)),
        'metadata_version':pn.__version__,'notice':NOTICE}
