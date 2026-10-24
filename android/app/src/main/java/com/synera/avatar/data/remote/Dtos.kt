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
)

@Serializable
data class LoginResponse(val token: String, val user: UserDto)

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
data class ApiErrorBody(val error: ApiError)

@Serializable
data class ApiError(val code: String, val message: String)
