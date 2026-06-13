from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.recycleview import RecycleView
from kivy.properties import StringProperty
from kivy.lang import Builder
from kivy.clock import Clock
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
                    # Find category
                    group_title_match = re.search(r'group-title="([^"]+)"', line)
                    category = group_title_match.group(1) if group_title_match else "Uncategorized"
                    
                    # Find channel name
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

class IPTVApp(App):
    def build(self):
        return MainLayout()
        
    def play_video(self, url):
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(Uri.parse(url), "video/*")
            PythonActivity.mActivity.startActivity(intent)
        except Exception as e:
            print("Not running on Android or jnius not available. URL:", url)

if __name__ == '__main__':
    IPTVApp().run()
