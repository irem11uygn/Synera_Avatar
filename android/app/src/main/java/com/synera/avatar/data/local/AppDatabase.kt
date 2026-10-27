package com.synera.avatar.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [
        ProductEntity::class,
        CustomerEntity::class,
        LotEntity::class,
        StockEntity::class,
        SyncMetaEntity::class,
        SaleEntity::class,
        SaleLineEntity::class,
    ],
    version = 4,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun masterData(): MasterDataDao

    abstract fun sales(): SalesDao

    companion object {
        fun create(context: Context): AppDatabase =
            Room.databaseBuilder(context, AppDatabase::class.java, "avatar.db")
                .addMigrations(MIGRATION_1_2, MIGRATION_2_3, MIGRATION_3_4)
                .build()

        /** 1 → 2: senkron kaydına sunucu veri kümesi kimliği eklendi. */
        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE sync_meta ADD COLUMN datasetId TEXT")
            }
        }

        /** 2 → 3: cihazda satış (T-14). Tanımlar Room'un ürettiği şemayla birebir aynıdır (açılışta denetlenir). */
        val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "CREATE TABLE IF NOT EXISTS `sale` (`clientUuid` TEXT NOT NULL, `customerId` INTEGER NOT NULL, " +
                        "`soldAtMillis` INTEGER NOT NULL, `syncState` TEXT NOT NULL, `serverSaleNo` TEXT, " +
                        "`serverMessage` TEXT, PRIMARY KEY(`clientUuid`))",
                )
                db.execSQL(
                    "CREATE TABLE IF NOT EXISTS `sale_line` (`saleUuid` TEXT NOT NULL, `lineNo` INTEGER NOT NULL, " +
                        "`productId` INTEGER NOT NULL, `lotId` INTEGER NOT NULL, `lotNo` TEXT NOT NULL, " +
                        "`qtyMilli` INTEGER NOT NULL, `unitPriceCents` INTEGER NOT NULL, " +
                        "`amountCents` INTEGER NOT NULL, PRIMARY KEY(`saleUuid`, `lineNo`))",
                )
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_sale_line_lotId` ON `sale_line` (`lotId`)")
            }
        }

        /** 3 → 4: satışta ödeme türü (gün sonu kasa özeti için). */
        val MIGRATION_3_4 = object : Migration(3, 4) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE sale ADD COLUMN paymentMethod TEXT")
            }
        }
    }
}
