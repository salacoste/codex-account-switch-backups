use notify::{Config as NotifyConfig, RecommendedWatcher, RecursiveMode, Watcher};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::sync::mpsc::channel;
use std::time::Duration;
use tauri::{
    menu::{CheckMenuItem, Menu, MenuItem, Submenu},
    tray::{MouseButton, TrayIcon, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, Runtime,
};

#[derive(serde::Deserialize)]
struct Config {
    active_account: Option<String>,
}

struct AppState {
    active_account: Option<String>,
    accounts: Vec<String>,
}

fn load_state() -> AppState {
    let home = env::var("HOME").unwrap_or_default();
    let root = PathBuf::from(home).join(".codex-accounts");

    // 1. Get active
    let config_path = root.join("config.json");
    let mut active_account = None;
    if let Ok(content) = fs::read_to_string(&config_path) {
        if let Ok(json) = serde_json::from_str::<Config>(&content) {
            active_account = json.active_account;
        }
    }

    // 2. Get accounts (Personal Vault)
    let accounts_dir = root.join("accounts");
    let mut accounts = Vec::new();
    if let Ok(entries) = fs::read_dir(accounts_dir) {
        for entry in entries.flatten() {
            if entry.path().is_dir() {
                if let Some(name) = entry.file_name().to_str() {
                    if !name.starts_with('.') {
                        accounts.push(name.to_string());
                    }
                }
            }
        }
    }
    accounts.sort();

    AppState {
        active_account,
        accounts,
    }
}

fn build_tray_menu<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<Menu<R>> {
    let state = load_state();
    let active = state.active_account.unwrap_or_default();

    let open_i = MenuItem::with_id(app, "open", "Open Manager", true, None::<&str>)?;
    let add_i = MenuItem::with_id(app, "add", "Add Account...", true, None::<&str>)?;
    let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let sep = tauri::menu::PredefinedMenuItem::separator(app)?;

    let menu = Menu::with_items(app, &[&open_i, &sep])?;

    // Accounts Section
    let count = state.accounts.len();
    if count > 0 {
        let header_title = if active.is_empty() {
            format!("Accounts ({})", count)
        } else {
            format!("Active: {} ({})", active, count)
        };

        let header = MenuItem::with_id(app, "disabled", header_title, false, None::<&str>)?;
        menu.append(&header)?;
        menu.append(&add_i)?; // "Add Account" near the list
        menu.append(&sep)?;

        for name in state.accounts {
            let is_active = name == active;
            let id = format!("switch:{}", name);
            let item = CheckMenuItem::with_id(app, &id, &name, true, is_active, None::<&str>)?;
            item.set_checked(is_active)?;
            menu.append(&item)?;
        }
        menu.append(&sep)?;
    } else {
        // No accounts
        menu.append(&add_i)?;
        menu.append(&sep)?;
    }

    menu.append(&quit_i)?;
    Ok(menu)
}

fn update_tray<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    if let Some(tray) = app.tray_by_id("main") {
        let menu = build_tray_menu(app)?;
        tray.set_menu(Some(menu))?;
        // Also emit event to frontend
        let _ = app.emit("tray-config-changed", ());
    }
    Ok(())
}

fn start_watcher<R: Runtime>(app: AppHandle<R>) {
    std::thread::spawn(move || {
        let home = env::var("HOME").unwrap_or_default();
        let config_path = PathBuf::from(home)
            .join(".codex-accounts")
            .join("config.json");

        // Channel to receive events
        let (tx, rx) = channel();

        // Create watcher
        let mut watcher: Box<dyn Watcher> =
            if let Ok(w) = RecommendedWatcher::new(tx, NotifyConfig::default()) {
                Box::new(w)
            } else {
                eprintln!("Failed to create watcher");
                return;
            };

        // Watch the file (or parent dir if file doesn't exist yet, but app ensures it exists)
        // We watch the FILE itself.
        if let Err(e) = watcher.watch(&config_path, RecursiveMode::NonRecursive) {
            eprintln!("Failed to watch config: {:?}", e);
            return;
        }

        loop {
            match rx.recv() {
                Ok(Ok(event)) => {
                    // Check if it's a write or modify
                    // notify 6.0 events can be complex, but any event on this file is worth a reload
                    if event.kind.is_modify() || event.kind.is_create() {
                        let app_clone = app.clone();
                        let app_for_closure = app_clone.clone();
                        // Debounce slightly or just run?
                        // Run on main thread to update tray
                        let _ = app_clone.run_on_main_thread(move || {
                            let _ = update_tray(&app_for_closure);
                        });
                    }
                }
                Ok(Err(e)) => eprintln!("Watch error: {:?}", e),
                Err(_) => break, // Channel closed
            }
        }
    });
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Log setup
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let menu = build_tray_menu(app.handle())?;

            let _tray = TrayIconBuilder::with_id("main")
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .on_menu_event(move |app, event| {
                    let id = event.id.as_ref();
                    if id == "quit" {
                        app.exit(0);
                    } else if id == "open" || id == "add" {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                            if id == "add" {
                                let _ = app.emit("tray-add-account", ());
                            }
                        }
                    } else if id.starts_with("switch:") {
                        let account_name = id.trim_start_matches("switch:");
                        let _ = app.emit("tray-switch-account", account_name);
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .on_tray_icon_event(|_tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        ..
                    } = event
                    {
                        // Handle click
                    }
                })
                .build(app)?;

            // Start Watcher
            start_watcher(app.handle().clone());

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
