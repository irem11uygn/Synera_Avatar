package com.synera.avatar.data.remote

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// API sözleşmesi: docs/api.md. Ondalıklar metin olarak gelir ve gider.

@Serializable
data class LoginRequest(val username: String, val password: String)

@Serializable
data class UserDto(
    val id: Long,
    val username: String,
    @SerialName("full_name") val fullName: String,
    val role: String,
    @SerialName("warehouse_id") val warehouseId: Long? = null,
    @SerialName("warehouse_code") val warehouseCode: String? = null,
    /** Yöneticinin verdiği geçici şifreyle girildi: yeni şifre belirlenmeden eşitleme yapılamaz. */
    @SerialName("must_change_password") val mustChangePassword: Boolean = false,
)

@Serializable
data class LoginResponse(val token: String, val user: UserDto)

@Serializable
data class ChangePasswordRequest(
    @SerialName("current_password") val currentPassword: String,
    @SerialName("new_password") val newPassword: String,
)

@Serializable
data class ProductDto(
    val id: Long,
    val code: String,
    val name: String,
    @SerialName("base_unit") val baseUnit: String,
    @SerialName("unit_weight_kg") val unitWeightKg: String? = null,
    @SerialName("sale_price") val salePrice: String? = null,
    val active: Boolean,
)

@Serializable
data class CustomerDto(
    val id: Long,
    val code: String,
    val name: String,
    @SerialName("contact_person") val contactPerson: String? = null,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
)

@Serializable
data class LotDto(
    val id: Long,
    @SerialName("lot_no") val lotNo: String,
    @SerialName("product_id") val productId: Long,
    @SerialName("expiry_date") val expiryDate: String? = null,
    val status: String,
)

@Serializable
data class StockDto(@SerialName("lot_id") val lotId: Long, val qty: String)

@Serializable
data class PullResponse(
    @SerialName("dataset_id") val datasetId: String,
    @SerialName("next_since") val nextSince: Long,
    val products: List<ProductDto>,
    val customers: List<CustomerDto>,
    val lots: List<LotDto>,
    val stock: List<StockDto>,
)

@Serializable
data class PushLineDto(
    @SerialName("lot_no") val lotNo: String,
    val qty: String,
    @SerialName("unit_price") val unitPrice: String,
)

@Serializable
data class PushSaleDto(
    @SerialName("client_uuid") val clientUuid: String,
    @SerialName("customer_id") val customerId: Long,
    @SerialName("warehouse_id") val warehouseId: Long,
    @SerialName("sold_at") val soldAt: String,
    val lines: List<PushLineDto>,
    @SerialName("payment_method") val paymentMethod: String? = null,
)

@Serializable
data class PushRequest(@SerialName("device_id") val deviceId: String, val sales: List<PushSaleDto>)

@Serializable
data class PushErrorDto(val code: String, val message: String)

@Serializable
data class PushResultDto(
    @SerialName("client_uuid") val clientUuid: String,
    val status: String,
    @SerialName("sale_no") val saleNo: String? = null,
    val warnings: List<String> = emptyList(),
    val error: PushErrorDto? = null,
)

@Serializable
data class PushResponse(val results: List<PushResultDto>)

@Serializable
data class ApiErrorBody(val error: ApiError)

@Serializable
data class ApiError(val code: String, val message: String)

@Serializable
data class DayTotalDto(val key: String, @SerialName("sale_count") val saleCount: Int, val amount: String)

@Serializable
data class DayReturnDto(
    @SerialName("return_no") val returnNo: String,
    @SerialName("customer_name") val customerName: String,
    @SerialName("lot_no") val lotNo: String,
    val qty: String,
    @SerialName("refund_amount") val refundAmount: String,
)

@Serializable
data class StockLeftDto(
    @SerialName("lot_no") val lotNo: String,
    @SerialName("product_name") val productName: String,
    @SerialName("base_unit") val baseUnit: String,
    @SerialName("expiry_date") val expiryDate: String? = null,
    val qty: String,
)

/** Gün sonu (GET /sync/day-end): satış elemanının kendi satışları, iadeleri ve aracında kalan mal. */
@Serializable
data class DayEndDto(
    val day: String,
    @SerialName("sale_count") val saleCount: Int,
    @SerialName("sales_amount") val salesAmount: String,
    @SerialName("refund_amount") val refundAmount: String,
    @SerialName("net_amount") val netAmount: String,
    @SerialName("by_payment") val byPayment: List<DayTotalDto>,
    val returns: List<DayReturnDto>,
    @SerialName("stock_left") val stockLeft: List<StockLeftDto>,
)

@Serializable
data class CountLineDto(@SerialName("lot_no") val lotNo: String, @SerialName("counted_qty") val countedQty: String)

@Serializable
data class StockCountRequest(
    @SerialName("warehouse_id") val warehouseId: Long,
    val note: String? = null,
    val lines: List<CountLineDto>,
)

@Serializable
data class CountResultLineDto(
    @SerialName("lot_no") val lotNo: String,
    @SerialName("product_name") val productName: String,
    @SerialName("base_unit") val baseUnit: String,
    @SerialName("system_qty") val systemQty: String,
    @SerialName("counted_qty") val countedQty: String,
    val difference: String,
)

@Serializable
data class StockCountResponse(
    @SerialName("count_no") val countNo: String,
    val lines: List<CountResultLineDto>,
    @SerialName("shortage_value") val shortageValue: String,
    @SerialName("surplus_lines") val surplusLines: Int,
)
