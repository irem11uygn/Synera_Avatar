// API tipleri OpenAPI tanımından üretilir (`npm run api:types`, ADR-002); burada kısa adlar verilir.
// Sözleşme değişirse web kodu derlenirken hata verir.

import type { components } from './schema'

type S = components['schemas']

export type User = S['UserOut']
export type LoginResponse = S['LoginResponse']

export type Product = S['app__api__master__ProductOut']
export type ProductInput = S['ProductIn']
export type ProductKind = S['ProductKind']
export type BaseUnit = S['BaseUnit']
export type Partner = S['PartnerOut']
export type PartnerInput = S['PartnerIn']
export type Warehouse = S['WarehouseOut']
export type WarehouseKind = S['WarehouseKind']

export type Purchase = S['PurchaseOut']
export type PurchaseInput = S['PurchaseIn']
export type PurchaseCostKind = S['PurchaseCostKind']

export type Lot = S['app__api__lots__LotOut']
export type LotDetail = S['LotDetailOut']
export type LotStatus = S['LotStatus']
export type LotOrigin = S['LotOrigin']
export type LinkProcess = S['LinkProcess']
export type Movement = S['MovementOut']
export type MovementType = S['MovementType']
export type StockRow = S['StockRowOut']

export type Transfer = S['TransferOut']
export type TransferInput = S['TransferIn']
export type TransferReason = S['TransferReason']

export type Recipe = S['RecipeOut']
export type RecipeInput = S['RecipeIn']
export type RecipeLineType = S['RecipeLineType']
export type Species = S['Species']
export type AllocationMethod = S['AllocationMethod']
export type Cutting = S['CuttingOut']
export type CuttingInput = S['CuttingIn']
export type ActualsInput = S['ActualsIn']
export type CuttingStatus = S['CuttingStatus']

export type Order = S['OrderOut']
export type OrderInput = S['OrderIn']
export type CompleteInput = S['CompleteIn']
export type OrderStatus = S['ProductionStatus']
