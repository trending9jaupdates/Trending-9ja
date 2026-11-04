/* ===== GOOGLE ADSENSE SETUP =====
  1) After Google approves you, replace ca-pub-XXXXXXXXXXXXXXXX with your publisher ID (also edit ads.txt).
  2) Paste each ad unit's numeric slot ID into slots (feed = lists, article = inside stories).
  Ads stay off (no empty boxes) until a real ID is set. */
var ADSENSE_CONFIG = {
  client: 'ca-pub-XXXXXXXXXXXXXXXX',
  slots: { feed: '', article: '' }
};
(function () {
  var c = ADSENSE_CONFIG.client;
  if (!c || /X{6}/.test(c)) return;
  document.documentElement.classList.add('ads-on');
  var m = document.createElement('meta'); m.name = 'google-adsense-account'; m.content = c; document.head.appendChild(m);
  var sc = document.createElement('script'); sc.async = true; sc.crossOrigin = 'anonymous';
  sc.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + encodeURIComponent(c);
  document.head.appendChild(sc);
})();

/* ===== PRIVATE VISITOR STATISTICS (Google Analytics 4) =====
   Paste your Measurement ID (looks like G-ABC123XYZ) between the quotes. Leave empty to switch tracking off.
   Only you can see the numbers, by logging in at analytics.google.com. */
var ANALYTICS_ID = 'G-5JYDBZ2MQZ';
(function () {
  if (!ANALYTICS_ID || !/^G-[A-Z0-9]+$/.test(ANALYTICS_ID)) return;
  var s = document.createElement('script'); s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(ANALYTICS_ID);
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { dataLayer.push(arguments); };
  gtag('js', new Date()); gtag('config', ANALYTICS_ID);
})();


/* ===== FEATURED POST (Offline Vibes) =====
   Edit this block only. It controls: the first card in Latest Buzz (home page),
   the card under the ESN advert on every story page, and news/offline-vibes.html.
   Set live:true when the details are filled in. Set live:false to switch it off everywhere. */
var FEATURED = {
  live: true,
  slug: 'offline-vibes',
  date: '2026-10-13',
  label: 'Featured',
  category: 'Music',
  title: 'Offline Vibes Want You to Go Offline and Feel the Music',
  summary: 'The act behind the new release is telling listeners to switch off the noise, reset and press play. Stream it on Spotify and YouTube Music.',
  image: 'https://i.scdn.co/image/ab67616d0000b27336b498407cd369d4831ca932',
  imageCredit: 'Cover art: Offline Vibes / Spotify',
  youtubeId: 'N3HUPqMu4Pk',
  paragraphs: [
    'Offline Vibes are asking listeners to step away from the noise with their newest release, now streaming on the major platforms.',
    'Spotify lists the release as the single "I\u2019m Just Vibing", out since 7 September 2026. The promotional post on Instagram presents it as a track called "Offline", made for anyone who has ever needed to disappear, reset, breathe and enjoy their own space.',
    'The campaign message is simple: do not just listen, feel it. Fans are encouraged to stream the song, share what they think and tag a friend who needs to unplug. The artwork says it is available on Spotify, YouTube Music and Audiomack.',
    'Use the buttons below to listen, and follow Offline Vibes on Instagram to keep up with new drops.'
  ],
  links: [
    { name: 'Spotify', url: 'https://open.spotify.com/album/5PdX6GpOBj5kiKdIkCw1eK', icon: 'fa-spotify' },
    { name: 'YouTube Music', url: 'https://music.youtube.com/watch?v=N3HUPqMu4Pk', icon: 'fa-youtube' }
  ],
  creator: { name: 'Offline Vibes', instagram: 'https://instagram.com/offlinevibes_sunoband' }
};

/* ===== NEWSLETTER SIGN-UP =====
   action = the form URL from your email service (Mailchimp, Buttondown, Formspree, MailerLite, Brevo...).
   Leave action empty ('') and the sign-up boxes stay hidden. emailField = the name of the email input your service expects. */
var NEWSLETTER_CONFIG = {
  action: '',
  emailField: 'EMAIL',
  hidden: { email_address_check: '', locale: 'en' },   // extra fields Brevo expects
  title: 'Get Trending9ja in your inbox',
  text: 'The biggest Nigerian news, entertainment and trends, delivered free. No spam, unsubscribe anytime.',
  button: 'Subscribe',
  placements: { feed: false, inPost: false, footer: true }   // set any to false to hide that box
};

var MONETAG_CONFIG = {};   /* Monetag removed */
