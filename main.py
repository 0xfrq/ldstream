from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import platform

# The single livestream URL to play
STREAM_URL = 'https://video.detik.com/trans7/smil:trans7.smil/index.m3u8'

class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        self.add_widget(Label(
            text="Trans7 Livestream Player",
            size_hint=(1, 0.2),
            font_size='24sp'
        ))
        
        btn = Button(
            text="PLAY STREAM",
            size_hint=(1, 0.8),
            font_size='32sp'
        )
        btn.bind(on_release=self.play_video)
        self.add_widget(btn)

    def play_video(self, instance):
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                VideoView = autoclass('android.widget.VideoView')
                Uri = autoclass('android.net.Uri')
                MediaController = autoclass('android.widget.MediaController')
                LinearLayout = autoclass('android.widget.LinearLayout')
                LayoutParams = autoclass('android.view.ViewGroup')

                @run_on_ui_thread
                def show_native_video():
                    activity = PythonActivity.mActivity
                    
                    # Create native Android VideoView
                    vv = VideoView(activity)
                    vv.setVideoURI(Uri.parse(STREAM_URL))
                    
                    # Add playback controls
                    mc = MediaController(activity)
                    mc.setAnchorView(vv)
                    vv.setMediaController(mc)
                    
                    # Overlay on top of Kivy
                    layout = LinearLayout(activity)
                    layout.addView(vv, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
                    
                    activity.addContentView(layout, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
                    
                    vv.start()
                    
                show_native_video()
            except Exception as e:
                print("Failed to launch Android native view:", e)
        else:
            print(f"Running on desktop. URL: {STREAM_URL}")
            print("Please run on Android or install gstreamer to view on Linux.")

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
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        PythonActivity.mActivity.runOnUiThread(_Runnable())
    return wrapper

class IPTVApp(App):
    def build(self):
        return MainLayout()

if __name__ == '__main__':
    IPTVApp().run()
