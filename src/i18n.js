export const LANGS = { en: 'English', hi: 'हिन्दी', mr: 'मराठी', gu: 'ગુજરાતી', ta: 'தமிழ்' };
export const SPEECH = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN', gu: 'gu-IN', ta: 'ta-IN' };
const S = {
  en: { dashboard: 'Dashboard', neworder: 'New Order', orders: 'Order History', catalog: 'Catalog & Stock', inventory: 'Inventory & Stock', customers: 'Customers', memory: 'Vyapaar Memory', insights: 'Insights', settings: 'Settings',
    namaste: 'Namaste, Shopkeeper!', ready: "Your shop is ready. Let's take your next order.", speak: 'Speak Your Order', manual: 'Create Order Manually', logout: 'Log out',
    profile: 'Edit your profile', language: 'Choose your language', langsub: 'The app will be shown in this language.', save: 'Save changes', saved: 'Saved', name: 'Your name', shop: 'Shop name', email: 'Email', phone: 'Mobile number', address: 'Shop address' },
  hi: { dashboard: 'डैशबोर्ड', neworder: 'नया ऑर्डर', orders: 'ऑर्डर इतिहास', catalog: 'प्रोडक्ट कैटलॉग', inventory: 'इन्वेंटरी और स्टॉक', customers: 'ग्राहक', memory: 'व्यापार मेमोरी', insights: 'इनसाइट्स', settings: 'सेटिंग्स',
    namaste: 'नमस्ते, दुकानदार जी!', ready: 'आपकी दुकान तैयार है। अगला ऑर्डर लेते हैं।', speak: 'बोलकर ऑर्डर दें', manual: 'हाथ से ऑर्डर बनाएं', logout: 'लॉग आउट',
    profile: 'अपनी प्रोफ़ाइल बदलें', language: 'अपनी भाषा चुनें', langsub: 'ऐप इसी भाषा में दिखेगा।', save: 'बदलाव सहेजें', saved: 'सहेजा गया', name: 'आपका नाम', shop: 'दुकान का नाम', email: 'ईमेल', phone: 'मोबाइल नंबर', address: 'दुकान का पता' },
  mr: { dashboard: 'डॅशबोर्ड', neworder: 'नवीन ऑर्डर', orders: 'ऑर्डर इतिहास', catalog: 'प्रोडक्ट कॅटलॉग', inventory: 'इन्व्हेंटरी आणि स्टॉक', customers: 'ग्राहक', memory: 'व्यापार मेमरी', insights: 'इनसाइट्स', settings: 'सेटिंग्ज',
    namaste: 'नमस्कार, दुकानदार!', ready: 'तुमचे दुकान तयार आहे. पुढची ऑर्डर घेऊया.', speak: 'बोलून ऑर्डर द्या', manual: 'हाताने ऑर्डर तयार करा', logout: 'लॉग आउट',
    profile: 'तुमची प्रोफाइल बदला', language: 'तुमची भाषा निवडा', langsub: 'अॅप या भाषेत दिसेल.', save: 'बदल जतन करा', saved: 'जतन केले', name: 'तुमचे नाव', shop: 'दुकानाचे नाव', email: 'ईमेल', phone: 'मोबाइल नंबर', address: 'दुकानाचा पत्ता' },
  gu: { dashboard: 'ડેશબોર્ડ', neworder: 'નવો ઓર્ડર', orders: 'ઓર્ડર ઇતિહાસ', catalog: 'પ્રોડક્ટ કેટલોગ', inventory: 'ઇન્વેન્ટરી અને સ્ટોક', customers: 'ગ્રાહકો', memory: 'વ્યાપાર મેમરી', insights: 'ઇનસાઇટ્સ', settings: 'સેટિંગ્સ',
    namaste: 'નમસ્તે, દુકાનદાર!', ready: 'તમારી દુકાન તૈયાર છે. આગલો ઓર્ડર લઈએ.', speak: 'બોલીને ઓર્ડર આપો', manual: 'હાથે ઓર્ડર બનાવો', logout: 'લૉગ આઉટ',
    profile: 'તમારી પ્રોફાઇલ બદલો', language: 'તમારી ભાષા પસંદ કરો', langsub: 'એપ આ ભાષામાં દેખાશે.', save: 'ફેરફાર સાચવો', saved: 'સાચવ્યું', name: 'તમારું નામ', shop: 'દુકાનનું નામ', email: 'ઇમેઇલ', phone: 'મોબાઇલ નંબર', address: 'દુકાનનું સરનામું' },
  ta: { dashboard: 'டாஷ்போர்டு', neworder: 'புதிய ஆர்டர்', orders: 'ஆர்டர் வரலாறு', catalog: 'பொருள் பட்டியல்', inventory: 'இருப்பு', customers: 'வாடிக்கையாளர்கள்', memory: 'வியாபார நினைவகம்', insights: 'நுண்ணறிவு', settings: 'அமைப்புகள்',
    namaste: 'வணக்கம், கடைக்காரரே!', ready: 'உங்கள் கடை தயார். அடுத்த ஆர்டரை எடுப்போம்.', speak: 'பேசி ஆர்டர் செய்யுங்கள்', manual: 'கைமுறையாக ஆர்டர் உருவாக்கு', logout: 'வெளியேறு',
    profile: 'உங்கள் சுயவிவரத்தை திருத்துங்கள்', language: 'உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்', langsub: 'ஆப் இந்த மொழியில் தெரியும்.', save: 'மாற்றங்களைச் சேமி', saved: 'சேமிக்கப்பட்டது', name: 'உங்கள் பெயர்', shop: 'கடை பெயர்', email: 'மின்னஞ்சல்', phone: 'மொபைல் எண்', address: 'கடை முகவரி' } };
export const tr = (lang, k) => (S[lang] && S[lang][k]) || S.en[k] || k;
