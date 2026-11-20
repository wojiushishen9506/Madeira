import Foundation
import SwiftUI

enum MadeiraLanguage: String, CaseIterable {
    case system, simplifiedChinese = "zh-Hans", english = "en", german = "de", spanish = "es",
         korean = "ko", brazilianPortuguese = "pt-BR", russian = "ru"

    static let key = "madeira.interfaceLanguage"
    static var current: Self { Self(rawValue: UserDefaults.standard.string(forKey: key) ?? "") ?? .system }

    var locale: Locale {
        self == .system ? .autoupdatingCurrent : Locale(identifier: rawValue)
    }

    var nativeName: String {
        switch self {
        case .system: return L("System language")
        case .simplifiedChinese: return "简体中文"
        case .english: return "English"
        case .german: return "Deutsch"
        case .spanish: return "Español"
        case .korean: return "한국어"
        case .brazilianPortuguese: return "Português (Brasil)"
        case .russian: return "Русский"
        }
    }

    private static let bundles: [Self: Bundle] = Dictionary(uniqueKeysWithValues: allCases.compactMap { language in
        guard language != .system,
              let url = Bundle.main.url(forResource: language.rawValue, withExtension: "lproj"),
              let bundle = Bundle(url: url) else { return nil }
        return (language, bundle)
    })

    func localized(_ key: String) -> String {
        let bundle = self == .system ? Bundle.main : Self.bundles[self]
        return bundle?.localizedString(forKey: key, value: key, table: "Localizable") ?? key
    }
}

struct MadeiraLanguagePicker: View {
    @AppStorage(MadeiraLanguage.key) private var language = MadeiraLanguage.system

    var body: some View {
        Picker("Interface language", selection: $language) {
            ForEach(MadeiraLanguage.allCases, id: \.self) { option in
                if option == .system {
                    Text("System language").tag(option)
                } else {
                    Text(verbatim: option.nativeName).tag(option)
                }
            }
        }
        .pickerStyle(.menu)
    }
}

@main
struct MadeiraApp: App {
    @AppStorage(MadeiraLanguage.key) private var language = MadeiraLanguage.system

    init() {
        // Opt-in iPhone pointer experiments (PhonePointer.m): before any scene exists.
        madeira_phone_pointer_setup()
        // madeira-bcd: the Metal Performance HUD's performance insights (the
        // notes that stack up left of its panel: shader compiles, similar render
        // passes, blit encoders) cover the game. Off unless madeira.cfg says
        // env.MTL_HUD_INSIGHTS_ENABLED = 1, which is exported later and wins.
        setenv("MTL_HUD_INSIGHTS_ENABLED", "0", 0)
        // Host pads as Windows.Gaming.Input gamepads (upstream's opt-in provider, willfaust/wine #40):
        // on by default here; madeira.cfg env.MADEIRA_WGI_HOST_PADS = 0 is exported later and wins.
        setenv("MADEIRA_WGI_HOST_PADS", "1", 0)
        // ml1172: read the screen on the main thread; library entries, whose
        // default Resolution comes from it, are also made on other threads.
        _ = ResolutionChoices.screen
        // A sign-in an installer left goes into the Keychain before anything else runs
        // (SigningRefresh.swift), only while the refresh is switched on.
        if SigningRefresh.enabled { SigningAccountStore.takeIn() }
        // Use one profile before Wine or Steam Cloud reads the prefix.
        ProfileUnification.run()
        // Games and downloads keep going when Madeira leaves the screen (BackgroundRun.swift).
        BackgroundRun.shared.start()
        // Read the cached library before the first grid page is built.
        if LibraryGridArm.enabled, SteamOwnedLibrary.enabled { SteamOwnedLibrary.shared.start() }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(\.locale, language.locale)
                .background(InteractionFrameRateInstaller())   // touch frame-rate request (New library grid)
                .modifier(ClaimGamepadEvents())
                .onAppear {
                    ExternalDrives.shared.mountAll()
                    GamepadInput.shared.start()
                    HardwareInput.shared.start()
                    JITNetworkShortcut.shared.restoreLeftover()   // also starts its network path monitor
                    WineGeckoModel.shared.installAutomatically()  // on Wi-Fi, so Wine never asks (WineGecko.swift)
                    AchievementWatcher.shared.start()             // unlock banners from Steam's stats files (SteamAchievements.swift)
                    ClaudeHelp.install()                          // the fixes guide beside madeira-log.txt (ClaudeHelp.swift)
                }
                // madeira://jit-network/... (the Madeira JIT shortcut returning, JITNetwork.swift),
                // else a shared game setup (a .madeirasetup file or madeira://setup?d=..., GameSetupShare.swift),
                // else madeira://play?exe=... (Home Screen shortcuts, SavesAndShortcuts.swift).
                .onOpenURL { url in
                    if JITNetworkShortcut.shared.handle(url) || GameSetupInbox.shared.handle(url) { return }
                    ShortcutRouter.shared.handle(url)
                }
        }
    }
}
