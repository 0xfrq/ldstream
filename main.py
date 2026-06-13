from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.recycleview import RecycleView
from kivy.properties import StringProperty
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.utils import platform
from kivy.uix.video import Video
from kivy.uix.popup import Popup
import urllib.request
import threading
import re

Builder.load_string('''
<ChannelItem>:
    on_release: app.play_video(self.url)

<MainLayout>:
    orientation: 'vertical'
    Spinner:
        id: category_spinner
        text: 'Loading Categories...'
        size_hint_y: 0.1
        on_text: root.update_channels(self.text)
    RecycleView:
        id: rv
        viewclass: 'ChannelItem'
        RecycleBoxLayout:
            default_size: None, dp(48)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
''')

class ChannelItem(Button):
    url = StringProperty('')

class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.channels = []
        self.load_playlist()

    def load_playlist(self):
        threading.Thread(target=self._download_thread, daemon=True).start()

    def _download_thread(self):
        url = 'https://iptv-org.github.io/iptv/index.m3u'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
            
            lines = content.splitlines()
            categories = set()
            channels = []
            current_channel = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('#EXTINF:'):
                    group_title_match = re.search(r'group-title="([^"]+)"', line)
                    category = group_title_match.group(1) if group_title_match else "Uncategorized"
                    
                    name_parts = line.split(',')
                    name = name_parts[-1] if len(name_parts) > 1 else "Unknown"
                    
                    current_channel = {'name': name, 'category': category}
                    categories.add(category)
                elif line and not line.startswith('#'):
                    if current_channel:
                        current_channel['url'] = line
                        channels.append(current_channel)
                        current_channel = {}
            
            Clock.schedule_once(lambda dt: self._on_download_success(channels, categories))
            
        except Exception as e:
            print(f"Error loading playlist: {e}")
            Clock.schedule_once(lambda dt: self._on_download_error())

    def _on_download_success(self, channels, categories):
        self.channels = channels
        if categories:
            sorted_cats = sorted(list(categories))
            self.ids.category_spinner.values = sorted_cats
            self.ids.category_spinner.text = sorted_cats[0]
        else:
            self.ids.category_spinner.text = 'No categories found'

    def _on_download_error(self):
        self.ids.category_spinner.text = 'Error loading'

    def update_channels(self, category):
        if category in ['Loading Categories...', 'Error loading', 'No categories found']:
            return
        filtered_channels = [c for c in self.channels if c['category'] == category]
        self.ids.rv.data = [{'text': c['name'], 'url': c['url']} for c in filtered_channels]


# For Android native view we need some JNI wrappers if on android
if platform == 'android':
    from jnius import autoclass
    from runnable import Runnable # Usually provided via android.runnable but we can use PythonActivity
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    VideoView = autoclass('android.widget.VideoView')
    Uri = autoclass('android.net.Uri')
    MediaController = autoclass('android.widget.MediaController')
    LinearLayout = autoclass('android.widget.LinearLayout')
    ViewGroup = autoclass('android.view.ViewGroup')
    LayoutParams = autoclass('android.view.ViewGroup')


class IPTVApp(App):
    def build(self):
        return MainLayout()
        
    def play_video(self, url):
        # The internal Kivy Video player does NOT support M3U8 out-of-the-box reliably 
        # (which is why you see the "Image Not found" and GStreamer errors).
        # We MUST use a native player. Since you don't want external apps like VLC/MX,
        # we will create an IN-APP Android VideoView overlay!
        
        if platform == 'android':
            try:
                # We must modify Android UI elements on the Android UI thread!
                # jnius allows us to run code on the UI thread.
                @run_on_ui_thread
                def show_native_video():
                    activity = PythonActivity.mActivity
                    
                    # Create a VideoView
                    vv = VideoView(activity)
                    vv.setVideoURI(Uri.parse(url))
                    
                    # Add playback controls
                    mc = MediaController(activity)
                    mc.setAnchorView(vv)
                    vv.setMediaController(mc)
                    
                    # Add it directly to the app's root view
                    layout = LinearLayout(activity)
                    layout.addView(vv, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
                    
                    activity.addContentView(layout, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
                    
                    vv.start()
                    
                show_native_video()
            except Exception as e:
                print("Failed to launch Android native view:", e)
        else:
            # Fallback for desktop testing (will fail on desktop without gstreamer bad plugins, but fine)
            video = Video(source=url, state='play', options={'allow_stretch': True})
            self.popup = Popup(
                title="Kivy Video (Requires Desktop Codecs)", 
                content=video,
                size_hint=(0.95, 0.95)
            )
            self.popup.bind(on_dismiss=lambda popup: setattr(video, 'state', 'stop'))
            self.popup.open()


# Helper to run on Android UI Thread
def run_on_ui_thread(func):
    if platform != 'android':
        return func
    from jnius import PythonJavaClass, java_method
    class _Runnable(PythonJavaClass):
        __javainterfaces__ = ['java/lang/Runnable']
        __javacontext__ = 'app'
        @java_method('()V')
        def run(self):
            func()
    def wrapper():
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        PythonActivity.mActivity.runOnUiThread(_Runnable())
    return wrapper

if __name__ == '__main__':
    IPTVApp().run()
