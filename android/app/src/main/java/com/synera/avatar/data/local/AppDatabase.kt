package com.synera.avatar.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [ProductEntity::class, CustomerEntity::class, LotEntity::class, StockEntity::class, SyncMetaEntity::class],
    version = 2,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun masterData(): MasterDataDao

    companion object {
        fun create(context: Context): AppDatabase =
            Room.databaseBuilder(context, AppDatabase::class.java, "avatar.db")
                .addMigrations(MIGRATION_1_2)
                .build()

        /** 1 → 2: senkron kaydına sunucu veri kümesi kimliği eklendi. */
        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE sync_meta ADD COLUMN datasetId TEXT")
            }
        }
    }
}
