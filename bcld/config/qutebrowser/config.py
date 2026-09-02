from qutebrowser.api import interceptor


# Add registrable domains here if an approved login or application flow needs
# to become a top-level page. Subdomains are included automatically.
ALLOWED_TOP_LEVEL_HOSTS = ('4thewords.com',)


def _is_allowed_top_level_url(url):
    if url.scheme().lower() != 'https':
        return False

    host = url.host().rstrip('.').lower()
    return any(
        host == allowed_host or host.endswith('.' + allowed_host)
        for allowed_host in ALLOWED_TOP_LEVEL_HOSTS
    )


def _block_external_top_level_navigation(info):
    if info.resource_type != interceptor.ResourceType.main_frame:
        return

    if not _is_allowed_top_level_url(info.request_url):
        info.block()


interceptor.register(_block_external_top_level_navigation)


config.load_autoconfig(True)
c.auto_save.session = False
c.colors.messages.error.fg = 'rgba(0,0,0,0)'
c.colors.messages.error.bg = 'rgba(0,0,0,0)'
c.colors.messages.error.border = 'rgba(0,0,0,0)'
c.colors.messages.info.bg = '#202020'
c.colors.messages.info.border = '#202020'
c.colors.messages.info.fg = 'white'
c.colors.tabs.selected.even.bg = 'white'
c.colors.tabs.selected.even.fg = 'black'
c.colors.tabs.selected.odd.bg = 'white'
c.colors.tabs.selected.odd.fg = 'black'
c.content.fullscreen.window = True
c.content.private_browsing = True
c.content.tls.certificate_errors = 'block'
c.fonts.default_size = '11pt'
c.fonts.default_family = 'Ubuntu'
c.fonts.tabs.selected = 'bold default_size default_family'
c.fonts.tabs.unselected = 'italic default_size default_family'
c.input.mode_override = 'passthrough'
c.input.mouse.rocker_gestures = True
c.messages.timeout = 5000
c.statusbar.show = 'never'
c.tabs.background = False
c.tabs.indicator.width = 0
c.tabs.last_close = 'startpage'
c.tabs.new_position.related = 'next'
c.tabs.new_position.unrelated = 'next'
c.tabs.show = 'multiple'

config.bind(
    '<F6>',
    'spawn --userscript /usr/bin/bcld_battery.sh',
    mode='passthrough',
)
