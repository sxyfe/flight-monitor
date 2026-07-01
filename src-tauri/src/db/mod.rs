pub mod repository;

use std::path::{Path, PathBuf};
use std::sync::Mutex;

use rusqlite::{Connection, OpenFlags};
use tauri::{AppHandle, Manager};

use crate::error::AppResult;

pub struct DbState {
    pub path: PathBuf,
    pub conn: Mutex<Connection>,
}

impl DbState {
    pub fn init(app: &AppHandle) -> AppResult<Self> {
        let dir = app
            .path()
            .app_data_dir()
            .map_err(|err| crate::error::AppError::Internal(err.to_string()))?;
        std::fs::create_dir_all(&dir).map_err(|err| crate::error::AppError::Internal(err.to_string()))?;
        let path = dir.join("flight-monitor.db");
        let conn = open_connection(&path)?;
        run_migrations(&conn)?;
        Ok(Self {
            path,
            conn: Mutex::new(conn),
        })
    }

    pub fn with_conn<T>(&self, f: impl FnOnce(&Connection) -> AppResult<T>) -> AppResult<T> {
        let conn = self
            .conn
            .lock()
            .map_err(|_| crate::error::AppError::Internal("database lock poisoned".into()))?;
        f(&conn)
    }
}

fn open_connection(path: &Path) -> AppResult<Connection> {
    Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE,
    )
    .map_err(Into::into)
}

fn run_migrations(conn: &Connection) -> AppResult<()> {
    let sql = include_str!("../../migrations/001_initial.sql");
    conn.execute_batch(sql)?;
    Ok(())
}
